from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.common.response import success
from app.api.deps import verify_api_token
from app.engine.registry import ChartRequest, calculate as engine_calculate, list_systems

router = APIRouter(prefix="/chart", tags=["chart"])


# ── 通用排盘接口 ──

class ChartBody(BaseModel):
    name: str = ""
    birth_date: str = ""
    birth_time: str = ""
    gender: str = ""
    question: str = ""
    extra: dict = {}


@router.get("/systems")
async def get_systems(_: str = Depends(verify_api_token)):
    """获取所有支持的计算系统列表。"""
    return success({"systems": list_systems()})


@router.post("/{system}")
async def create_chart(
    system: str, body: ChartBody,
    format: str = Query(default=""),
    _: str = Depends(verify_api_token),
):
    """通用排盘接口，支持所有 14 个引擎。"""
    req = ChartRequest(system=system, **body.model_dump())
    result = await engine_calculate(req)
    data = {
        "chart_id": result.chart_id,
        "system": result.system,
        "raw_data": result.raw_data,
        "text_summary": result.text_summary,
        "image_url": f"/files/charts/{result.chart_id}.png" if result.image_path else None,
    }
    if format == "tts":
        data = {"chart_id": result.chart_id, "tts_text": result.text_summary}
    return success(data)


# ── 便捷接口（各引擎独立路由，参数更语义化）──

class BirthInfoBody(BaseModel):
    """需要出生信息的引擎通用参数。"""
    name: str = Field(description="姓名")
    birth_date: str = Field(description="公历出生日期 YYYY-MM-DD")
    birth_time: str = Field(description="出生时间，如 14:00 / 下午2点 / 午")
    gender: str = Field(description="性别：男 或 女")
    question: str = ""


class DivinationBody(BaseModel):
    """占卜类引擎参数（不需要出生信息）。"""
    question: str = Field(default="", description="占问之事")
    birth_date: str = Field(default="", description="日期 YYYY-MM-DD，留空为今天")
    birth_time: str = Field(default="", description="时间，留空为当前")


class LiuyaoBody(BaseModel):
    yao_codes: list[int] = Field(description="六爻码，6个数字(1~4)列表")
    question: str = ""
    birth_date: str = ""
    gender: str = "男"


class HehunBody(BaseModel):
    name_a: str = Field(description="甲方姓名")
    birth_date_a: str = Field(description="甲方出生日期 YYYY-MM-DD")
    birth_time_a: str = Field(description="甲方出生时间")
    gender_a: str = Field(description="甲方性别")
    name_b: str = Field(description="乙方姓名")
    birth_date_b: str = Field(description="乙方出生日期 YYYY-MM-DD")
    birth_time_b: str = Field(description="乙方出生时间")
    gender_b: str = Field(description="乙方性别")


class QianwenBody(BaseModel):
    sign_type: str = Field(default="guanyin", description="签种: guanyin/huangdaxian/zhuge")
    question: str = ""


class JiemengBody(BaseModel):
    keyword: str = Field(description="梦境关键词")


class NameBody(BaseModel):
    name: str = Field(description="待分析姓名")


class JiriBody(BaseModel):
    activity: str = Field(description="事项: 结婚/搬家/开业 等")
    start_date: str = Field(default="", description="起始日期 YYYY-MM-DD")
    end_date: str = Field(default="", description="截止日期 YYYY-MM-DD")


class AlmanacBody(BaseModel):
    date: str = Field(default="", description="日期 YYYY-MM-DD，留空为今天")


async def _calc(system: str, **kwargs) -> dict:
    req = ChartRequest(system=system, **kwargs)
    result = await engine_calculate(req)
    return {
        "chart_id": result.chart_id,
        "system": result.system,
        "raw_data": result.raw_data,
        "text_summary": result.text_summary,
    }


def _today():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


@router.post("/ziwei/calc", summary="紫微斗数排盘")
async def calc_ziwei(body: BirthInfoBody, _: str = Depends(verify_api_token)):
    return success(await _calc("ziwei", name=body.name, birth_date=body.birth_date,
                               birth_time=body.birth_time, gender=body.gender))


@router.post("/bazi/calc", summary="八字排盘")
async def calc_bazi(body: BirthInfoBody, _: str = Depends(verify_api_token)):
    return success(await _calc("bazi", name=body.name, birth_date=body.birth_date,
                               birth_time=body.birth_time, gender=body.gender))


@router.post("/astrology/calc", summary="西方星盘")
async def calc_astrology(body: BirthInfoBody, _: str = Depends(verify_api_token)):
    return success(await _calc("astrology", name=body.name, birth_date=body.birth_date,
                               birth_time=body.birth_time, gender=body.gender))


@router.post("/meihua/calc", summary="梅花易数起卦")
async def calc_meihua(body: DivinationBody, _: str = Depends(verify_api_token)):
    return success(await _calc("meihua", name="占问", birth_date=body.birth_date or _today(),
                               birth_time=body.birth_time, gender="男", question=body.question))


@router.post("/liuyao/calc", summary="六爻排盘")
async def calc_liuyao(body: LiuyaoBody, _: str = Depends(verify_api_token)):
    return success(await _calc("liuyao", name="占问", birth_date=body.birth_date or _today(),
                               birth_time="6", gender=body.gender, question=body.question,
                               extra={"yao_codes": body.yao_codes}))


@router.post("/liuyao/verdict", summary="六爻算法断卦（直接 TTS，不走 LLM）")
async def verdict_liuyao(body: LiuyaoBody, _: str = Depends(verify_api_token)):
    """返回纯算法断卦结论。设备拿到 tts_text 字段即可直接朗读，无需经过 LLM。

    返回字段:
        chart_id   排盘 id
        gua_name   卦名
        verdict    完整断卦摘要 (含用神/月日生克/四神/吉凶倾向)
        tts_text   TTS 友好版口语化结论 (80~150 字)
        yongshen   用神信息 {qin6, positions, wuxing, source}
        four_gods  {yuan, ji, chou}
        guashen    卦身地支
    """
    result = await _calc(
        "liuyao", name="占问", birth_date=body.birth_date or _today(),
        birth_time="6", gender=body.gender, question=body.question,
        extra={"yao_codes": body.yao_codes},
    )
    a = result["raw_data"].get("analysis") or {}
    if "error" in a:
        return success({"chart_id": result["chart_id"], "error": a["error"]})
    return success({
        "chart_id": result["chart_id"],
        "gua_name": result["raw_data"]["data"].get("name"),
        "verdict": a.get("summary"),
        "tts_text": a.get("tts_text"),
        "yongshen": a.get("yongshen"),
        "four_gods": a.get("four_gods"),
        "guashen": a.get("guashen"),
    })


@router.post("/qimen/calc", summary="奇门遁甲")
async def calc_qimen(body: DivinationBody, _: str = Depends(verify_api_token)):
    return success(await _calc("qimen", name="占问", birth_date=body.birth_date or _today(),
                               birth_time=body.birth_time, gender="男", question=body.question))


@router.post("/liuren/calc", summary="大六壬")
async def calc_liuren(body: DivinationBody, guiren: int = Query(default=1),
                      _: str = Depends(verify_api_token)):
    return success(await _calc("liuren", name="占问", birth_date=body.birth_date or _today(),
                               birth_time=body.birth_time, gender="男", question=body.question,
                               extra={"guiren": str(guiren)}))


@router.post("/iching/calc", summary="周易筮法")
async def calc_iching(body: DivinationBody, _: str = Depends(verify_api_token)):
    return success(await _calc("iching", name="占问", birth_date=body.birth_date or _today(),
                               birth_time=body.birth_time, gender="男", question=body.question))


@router.post("/qianwen/calc", summary="求签")
async def calc_qianwen(body: QianwenBody, _: str = Depends(verify_api_token)):
    return success(await _calc("qianwen", name="求签", birth_date=_today(),
                               birth_time="0", gender="男", question=body.question,
                               extra={"type": body.sign_type}))


@router.post("/jiemeng/calc", summary="周公解梦")
async def calc_jiemeng(body: JiemengBody, _: str = Depends(verify_api_token)):
    return success(await _calc("jiemeng", name="解梦", birth_date=_today(),
                               birth_time="0", gender="男", question=body.keyword))


@router.post("/name/calc", summary="姓名五格分析")
async def calc_name(body: NameBody, _: str = Depends(verify_api_token)):
    return success(await _calc("name_analysis", name=body.name, birth_date="2000-01-01",
                               birth_time="0", gender="男"))


@router.post("/hehun/calc", summary="八字合婚")
async def calc_hehun(body: HehunBody, _: str = Depends(verify_api_token)):
    return success(await _calc("hehun", name=body.name_a, birth_date=body.birth_date_a,
                               birth_time=body.birth_time_a, gender=body.gender_a,
                               extra={
                                   "spouse_birth_date": body.birth_date_b,
                                   "spouse_birth_time": body.birth_time_b,
                                   "spouse_gender": body.gender_b,
                               }))


@router.post("/almanac/calc", summary="黄历查询")
async def calc_almanac(body: AlmanacBody, _: str = Depends(verify_api_token)):
    return success(await _calc("almanac", name="查询", birth_date=body.date or _today(),
                               birth_time="0", gender="男"))


@router.post("/jiri/calc", summary="黄道吉日查询")
async def calc_jiri(body: JiriBody, _: str = Depends(verify_api_token)):
    extra = {"start_date": body.start_date or _today()}
    if body.end_date:
        extra["end_date"] = body.end_date
    return success(await _calc("jiri", name="吉日查询", birth_date=extra["start_date"],
                               birth_time="0", gender="男", question=body.activity, extra=extra))
