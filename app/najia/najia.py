"""
纳甲六爻排盘核心类。
移植自 najia (bopo/najia, MIT License)，去除 arrow/jinja2/lunar_python 外部依赖。
"""
import logging
from datetime import datetime
from pathlib import Path

from .const import GUA5, GUA64, GUAS, SYMBOL, XING5, YAOS, ZHI5, ZHIS
from .utils import get_god6, get_guaci, get_najia, get_qin6, get_type, GZ5X, palace, set_shi_yao

logger = logging.getLogger(__name__)


class Najia:

    def __init__(self, verbose=None):
        self.verbose = min(verbose or 0, 2)
        self.bian = None  # 变卦
        self.hide = None  # 伏神
        self.data = None

    @staticmethod
    def _daily(date=None):
        """用本地 app.lunar 计算日期干支，替代原 lunar_python 依赖。"""
        from app.lunar import Solar

        solar = Solar.fromYmdHms(date.year, date.month, date.day, date.hour, 0, 0)
        lunar = solar.getLunar()
        ganzi = lunar.getBaZi()

        return {
            'xkong': lunar.getDayXunKong(),
            'gz': {
                'year': ganzi[0],
                'month': ganzi[1],
                'day': ganzi[2],
                'hour': ganzi[3],
            }
        }

    @staticmethod
    def _hidden(gong=None, qins=None):
        """计算伏神卦。"""
        if gong is None or qins is None:
            raise ValueError('gong and qins are required')

        if len(set(qins)) < 5:
            mark = YAOS[gong] * 2
            qin6 = [(get_qin6(XING5[int(GUA5[gong])], ZHI5[ZHIS.index(x[1])])) for x in get_najia(mark)]
            qinx = [GZ5X(x) for x in get_najia(mark)]
            seat = [qin6.index(x) for x in list(set(qin6).difference(set(qins)))]

            return {
                'name': GUA64.get(mark),
                'mark': mark,
                'qin6': qin6,
                'qinx': qinx,
                'seat': seat,
            }
        return None

    @staticmethod
    def _transform(params=None, gong=None):
        """计算变卦。"""
        if params is None:
            raise ValueError('params is required')

        if type(params) == str:
            params = [int(x) for x in params]

        if len(params) < 6:
            raise ValueError('params must have 6 elements')

        if 3 in params or 4 in params:
            mark = ''.join(['1' if v in [1, 4] else '0' for v in params])
            qin6 = [(get_qin6(XING5[int(GUA5[gong])], ZHI5[ZHIS.index(x[1])])) for x in get_najia(mark)]
            qinx = [GZ5X(x) for x in get_najia(mark)]

            return {
                'name': GUA64.get(mark),
                'mark': mark,
                'qin6': qin6,
                'qinx': qinx,
                'gong': GUAS[palace(mark, set_shi_yao(mark)[0])],
            }
        return None

    def compile(self, params=None, gender=None, date=None, title=None, guaci=False, day=None, **kwargs):
        """
        根据参数编译卦。

        :param params: 6个数字列表 (1=单/阳, 2=拆/阴, 3=重/老阳动, 4=交/老阴动)
        :param gender: 性别
        :param date: 日期字符串 (YYYY-MM-DD HH:MM) 或 datetime 对象
        :param title: 卦题
        :param guaci: 是否显示卦辞
        :param day: 可选的日干支覆盖
        """
        title = title or ''

        if date is None:
            solar = datetime.now()
        elif isinstance(date, str):
            # 支持 "YYYY-MM-DD HH:MM" 或 "YYYY-MM-DD"
            for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    solar = datetime.strptime(date, fmt)
                    break
                except ValueError:
                    continue
            else:
                solar = datetime.now()
        else:
            solar = date

        lunar = self._daily(solar)
        gender = gender or ''

        # 卦码
        mark = ''.join([str(int(p) % 2) for p in params])
        shiy = set_shi_yao(mark)  # 世应爻
        gong = palace(mark, shiy[0])  # 卦宫
        name = GUA64[mark]  # 卦名

        # 六亲
        qin6 = [(get_qin6(XING5[int(GUA5[gong])], ZHI5[ZHIS.index(x[1])])) for x in get_najia(mark)]
        qinx = [GZ5X(x) for x in get_najia(mark)]

        # 六神
        god6 = get_god6(lunar['gz']['day'])

        # 动爻位置
        dong = [i for i, x in enumerate(params) if x > 2]

        # 伏神
        hide = self._hidden(gong, qin6)

        # 变卦
        bian = self._transform(params=params, gong=gong)

        self.data = {
            'params': params,
            'gender': gender,
            'title': title,
            'guaci': guaci,
            'solar': solar,
            'lunar': lunar,
            'god6': god6,
            'dong': dong,
            'name': name,
            'mark': mark,
            'gong': GUAS[gong],
            'shiy': shiy,
            'qin6': qin6,
            'qinx': qinx,
            'bian': bian,
            'hide': hide,
        }

        return self

    def render(self):
        """渲染卦象文本输出（纯 Python，无 jinja2 依赖）。"""
        rows = self.data
        symbal = SYMBOL[self.verbose]
        empty = '\u3000' * 6

        rows['dyao'] = [symbal[x] if x in (3, 4) else '' for x in rows['params']]

        rows['main'] = {}
        rows['main']['mark'] = [symbal[int(x)] for x in rows['mark']]
        rows['main']['type'] = get_type(rows['mark'])
        rows['main']['gong'] = rows['gong']
        rows['main']['name'] = rows['name']
        rows['main']['indent'] = '\u3000' * 2

        if rows.get('hide'):
            rows['hide']['qin6'] = [
                ' %s%s ' % (rows['hide']['qin6'][x], rows['hide']['qinx'][x])
                if x in rows['hide']['seat'] else empty
                for x in range(6)
            ]
            rows['main']['indent'] += empty
        else:
            rows['main']['indent'] += '\u3000'
            rows['hide'] = {'qin6': ['  ' for _ in range(6)]}

        rows['main']['display'] = '{indent}{name} ({gong}-{type})'.format(**rows['main'])

        if rows.get('bian'):
            hide = 19 if rows.get('hide') and rows['hide'].get('seat') else 8
            rows['bian']['type'] = get_type(rows['bian']['mark'])
            rows['bian']['indent'] = (hide - len(rows['main']['display'])) * '\u3000'

            if rows['bian']['qin6']:
                rows['bian']['qin6'] = [
                    f'{rows["bian"]["qin6"][x]}{rows["bian"]["qinx"][x]}'
                    if x in rows['dong']
                    else f'  {rows["bian"]["qin6"][x]}{rows["bian"]["qinx"][x]}'
                    for x in range(6)
                ]

            if rows['bian']['mark']:
                rows['bian']['mark'] = [symbal[int(c)] for c in rows['bian']['mark']]
        else:
            rows['bian'] = {'qin6': [' ' for _ in range(6)], 'mark': [' ' for _ in range(6)]}

        shiy = []
        for x in range(6):
            if x == rows['shiy'][0] - 1:
                shiy.append('世')
            elif x == rows['shiy'][1] - 1:
                shiy.append('应')
            else:
                shiy.append('  ')
        rows['shiy'] = shiy

        if rows['guaci']:
            rows['guaci'] = get_guaci(rows['name'])

        # 用 f-string 替代 jinja2 模板渲染
        return self._render_text(rows)

    @staticmethod
    def _render_text(r):
        """纯 Python 文本渲染，替代 jinja2 模板。"""
        lunar = r['lunar']
        solar = r['solar']
        lines = []

        # 日期头
        date_str = solar.strftime('%Y年%m月%d日 %H时')
        lines.append(f"公历: {date_str}")
        gz = lunar['gz']
        lines.append(f"干支: {gz['year']}年 {gz['month']}月 {gz['day']}日 {gz['hour']}时")
        lines.append(f"旬空: {lunar['xkong']}")

        if r.get('gender'):
            lines.append(f"性别: {r['gender']}")
        if r.get('title'):
            lines.append(f"卦题: {r['title']}")
        lines.append('')

        # 卦名
        lines.append(r['main']['display'])
        lines.append('')

        # 六爻排列 (从上到下: 第6爻到第1爻)
        for i in range(5, -1, -1):
            parts = []
            parts.append(f"{r['god6'][i]}")
            parts.append(f"{r['qin6'][i]}{r['qinx'][i]}")
            parts.append(f"{r['main']['mark'][i]}")
            parts.append(f"{r['shiy'][i]}")

            if r['hide']['qin6'][i].strip():
                parts.append(f"伏:{r['hide']['qin6'][i].strip()}")

            if r['dyao'][i]:
                parts.append(f"{r['dyao'][i]}")
                parts.append(f"{r['bian']['mark'][i]}")
                parts.append(f"{r['bian']['qin6'][i]}")

            lines.append('  '.join(parts))

        if r.get('guaci') and isinstance(r['guaci'], str):
            lines.append('')
            lines.append(r['guaci'])

        return '\n'.join(lines)
