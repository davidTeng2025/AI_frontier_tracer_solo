# 工具函数
import requests
import json

"""
  视频列表获取：work_flow?workflow_id=7599486351155494954&space_id=7551631948008439848
  抖音视频文案提取：work_flow?workflow_id=7599546531909255177&space_id=7551631948008439848
"""

# 配置参数（全部预设好，函数无入参）
API_TOKEN = "pat_hfwkehfncaf****"  # 替换为你的 PAT
WORKFLOW_ID = "73664689170551*****"  # 替换为工作流 ID
APP_ID = "743962661420117****"  # 替换为应用 ID
BASE_URL = "https://api.coze.cn/v1/workflow/run"


def run_workflow_by_cozepy(api_token: str, workflow_id: str, parameters: dict | None = None):
    """
    使用 Coze 官方 Python SDK（cozepy）调用 workflow（示例）。

    - 入参：api_token、workflow_id、parameters
    - 注意：本项目 `requirements.txt` 当前未包含 `cozepy`，如需使用请先安装：
      `pip install cozepy`
    """
    # coze_api_base = "https://api.coze.cn/v1/workflow/run"
    if not isinstance(api_token, str) or not api_token.strip():
        raise ValueError("api_token 不能为空")
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValueError("workflow_id 不能为空")
    if parameters is not None and not isinstance(parameters, dict):
        raise TypeError("parameters 必须是 dict 或 None")

    try:
        # Our official coze sdk for Python [cozepy](https://github.com/coze-dev/coze-py)
        from cozepy import COZE_CN_BASE_URL  # type: ignore[import-not-found]
        from cozepy import Coze, TokenAuth  # type: ignore[import-not-found]  # noqa
    except ImportError as e:
        raise ImportError("未安装 `cozepy`，请先执行 `pip install cozepy` 后再调用该函数") from e

    # The default access is api.coze.com, but if you need to access api.coze.cn,
    # please use base_url to configure the api endpoint to access
    coze_api_base = COZE_CN_BASE_URL

    # Init the Coze client through the access_token.
    coze = Coze(auth=TokenAuth(token=api_token), base_url=coze_api_base)

    # Call the coze.workflows.runs.create method to create a workflow run.
    try:
        workflow = coze.workflows.runs.create(
            workflow_id=workflow_id,
            parameters=parameters or {},
        )
    except Exception as e:
        raise RuntimeError(
            f"调用 coze.workflows.runs.create 失败：workflow_id={workflow_id!r}，"
            f"parameters_keys={list((parameters or {}).keys())!r}"
        ) from e

    if workflow is None:
        raise RuntimeError("coze.workflows.runs.create 返回 None")

    data = getattr(workflow, "data", None)
    if data is None:
        raise RuntimeError(f"workflow.data 为空，workflow={workflow!r}")

    # 尽量把明显的失败情况提前抛出，避免下游 get() 崩溃
    if isinstance(data, dict):
        # 常见字段：success / code / msg（不同工作流可能不同）
        if data.get("success") is False:
            raise RuntimeError(f"工作流执行失败：{data.get('msg') or data}")
        if "code" in data and data.get("code") not in (0, 200):
            raise RuntimeError(f"工作流返回异常 code={data.get('code')}: {data.get('msg') or data}")

    data_res = json.loads(data)
    print("workflow.data", data_res)
    return data_res

#     # 请求体
#     data = {
#         "workflow_id": WORKFLOW_ID,
#         "app_id": APP_ID,
#         "parameters": {
#             "user_id": "12345",
#             "user_name": "George",  # 替换为工作流实际需要的参数
#         },
#     }

#     # 发送请求
#     response = requests.post(BASE_URL, headers=headers, data=json.dumps(data))
#     result = response.json()

#     # 处理响应
#     if result.get("code") == 0:
#         print("执行成功！")
#         print("输出结果:", result.get("data"))
#         print("调试链接:", result.get("debug_url"))  # 用于调试工作流执行过程
#     else:
#         print(f"执行失败: {result.get('msg')}")

#     return result

# 获取视频列表
def get_video_list(max_cursor: int = 0, count: int = 20, input_url: str | None = None):
    """
    返回视频列表数据示例
    {
        "code": {
            "has_more": true,
            "list": [
            {
                "avatar": "https://p3.douyinpic.com/aweme-avatar/tos-cn-avt-0015_ac94673e8aea988adce96b9ae4c25c9f~tplv-dy-shrink-adapter:144:144.heic?from=327834062",
                "caption": "Gemini 3发布后，这5个开发者给自己的人生装上了外挂。\n27年程序员老兵：用AI写出多部长篇小说，一边敲代码一边圆武侠梦 ；\n硬核奶爸：手搓本地AI操作系统，把私教装进孩子口袋；\nAI安全研究员：把AI变成科研副驾，打破思维墙；\n有效加速主义者：打造AI全自动分身，让AI替自己看新闻处理琐事；\n全栈讲师：降低新手学习门槛，把技术文档自动变成PPT；\n本期视频，产品君连线5位GDE谷歌开发者专家，带你拆解AI时代的超级个体，听听他们给普通人的真诚建议。\n\n#前沿科技趋势发布月 #抖音知识年终大赏  #AI新星计划 #AI #Google",
                "cover": "https://p3-sign.douyinpic.com/tos-cn-i-dy/e8811a98fa034f85973168d834c183bd~tplv-dy-resize-walign:360:q75.jpeg?lk3s=138a59ce&x-expires=1770620400&x-signature=lTgmoJ5RXF%2BqVBoi7bu1o30Pj3c%3D&from=327834062&s=PackSourceEnum_PUBLISH&se=false&sc=cover&biz_tag=aweme_video&l=202601261530054015C224E0963CA174FB",
                "create_time": 1767098192,
                "duration": 624664,
                "item_id": "7589628862217112841",
                "link": "https://www.douyin.com/video/7589628862217112841",
                "music": {
                "music_author": "产品君",
                "music_duration": 624,
                "music_title": "@产品君创作的原声",
                "music_url": "https://sf5-hl-cdn-tos.douyinstatic.com/obj/ies-music/7589629268636863251.mp3"
                },
                "nickname": "产品君",
                "short_id": "65180295651",
                "statistics": {
                "admire_count": 0,
                "collect_count": 2491,
                "comment_count": 147,
                "digg_count": 10094,
                "download_count": 1,
                "exposure_count": 0,
                "forward_count": 0,
                "live_watch_count": 0,
                "lose_comment_count": 0,
                "lose_count": 0,
                "play_count": 0,
                "share_count": 535,
                "whatsapp_share_count": 0
                },
                "title": "抖音前沿科技30X30｜采访AI超级个体 Gemini 3发布后，这5个开发者给自己的人生装上了外挂。\n27年程序员老兵：用AI写出多部长篇小说，一边敲代码一边圆武侠梦 ；\n硬核奶爸：手搓本地AI操作系统，把私教装进孩子口袋；\nAI安全研究员：把AI变成科研副驾，打破思维墙；\n有效加速主义者：打造AI全自动分身，让AI替自己看新闻处理琐事；\n全栈讲师：降低新手学习门槛，把技术文档自动变成PPT；\n本期视频，产品君连线5位GDE谷歌开发者专家，带你拆解AI时代的超级个体，听听他们给普通人的真诚建议。 \n#前沿科技趋势发布月 #抖音知识年终大赏  #AI新星计划 #AI #Google",
                "unique_id": "aipmgo",
                "video_download_addr": "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d59s9mnog65o6br9gt10&line=1&file_id=bc4221c4b9cd4091b3809b6fc4286036&sign=73479d72c8d3e7988751123fffd8c7e2&is_play_url=1&source=PackSourceEnum_PUBLISH"
            },
            {
                "avatar": "https://p3.douyinpic.com/aweme-avatar/tos-cn-avt-0015_ac94673e8aea988adce96b9ae4c25c9f~tplv-dy-shrink-adapter:144:144.heic?from=327834062",
                "caption": "开源视频制作Remotion Skills爆火\nAI编程开无限画布插件Pencil 爆火\n开源个人AI助手Clawdbot爆火，7成24小时给你打工\nClaude Excel插件更新\nRunway上线最强视频模型Gen 4.5\n字节开源视频参考模型OminiTransfer\n字节发布最强数字人直播模型FlowACT R1\n阿里开源最强文本转语音模型Qwen 3 TTS\n\n#AI新星计划 #抖音知识年终大赏  #AI #OpenAI #AIGC",
                "cover": "https://p26-sign.douyinpic.com/tos-cn-i-dy/a91f8ecc865e4e90bef58b3639b24a3c~tplv-dy-resize-walign:360:q75.jpeg?lk3s=138a59ce&x-expires=1770620400&x-signature=DV%2FtwuCiZr2rNMAYNFav1%2B5ylTY%3D&from=327834062&s=PackSourceEnum_PUBLISH&se=false&sc=cover&biz_tag=aweme_video&l=202601261530054015C224E0963CA174FB",
                "create_time": 1769348407,
                "duration": 140459,
                "item_id": "7599293185763855667",
                "link": "https://www.douyin.com/video/7599293185763855667",
                "music": {
                "music_author": "产品君",
                "music_duration": 140,
                "music_title": "@产品君创作的原声",
                "music_url": "https://sf5-hl-cdn-tos.douyinstatic.com/obj/ies-music/7599293579936221995.mp3"
                },
                "nickname": "产品君",
                "short_id": "65180295651",
                "statistics": {
                "admire_count": 0,
                "collect_count": 6846,
                "comment_count": 252,
                "digg_count": 10375,
                "download_count": 0,
                "exposure_count": 0,
                "forward_count": 0,
                "live_watch_count": 0,
                "lose_comment_count": 0,
                "lose_count": 0,
                "play_count": 0,
                "share_count": 2427,
                "whatsapp_share_count": 0
                },
                "title": "盘点一周AI大事(1月25日)｜Agent进化，24小时打工 开源视频制作Remotion Skills爆火\nAI编程开无限画布插件Pencil 爆火\n开源个人AI助手Clawdbot爆火，7成24小时给你打工\nClaude Excel插件更新\nRunway上线最强视频模型Gen 4.5\n字节开源视频参考模型OminiTransfer\n字节发布最强数字人直播模型FlowACT R1\n阿里开源最强文本转语音模型Qwen 3 TTS \n#AI新星计划 #抖音知识年终大赏  #AI #OpenAI #AIGC",
                "unique_id": "aipmgo",
                "video_download_addr": "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d5r1jkvog65i5t3brplg&line=1&file_id=1d9f92592313428dbeff9f48524f0844&sign=942b7c96da4efc50e8381fca2d5932a8&is_play_url=1&source=PackSourceEnum_PUBLISH"
            }
            ],
            "max_cursor": 1769348407000,
            "video_download_addr_array": [
            "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d59s9mnog65o6br9gt10&line=1&file_id=bc4221c4b9cd4091b3809b6fc4286036&sign=73479d72c8d3e7988751123fffd8c7e2&is_play_url=1&source=PackSourceEnum_PUBLISH",
            "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d5r1jkvog65i5t3brplg&line=1&file_id=1d9f92592313428dbeff9f48524f0844&sign=942b7c96da4efc50e8381fca2d5932a8&is_play_url=1&source=PackSourceEnum_PUBLISH"
            ]
        },
        "msg": "请求成功",
        "output": {
            "has_more": true,
            "list": [
            {
                "avatar": "https://p3.douyinpic.com/aweme-avatar/tos-cn-avt-0015_ac94673e8aea988adce96b9ae4c25c9f~tplv-dy-shrink-adapter:144:144.heic?from=327834062",
                "caption": "Gemini 3发布后，这5个开发者给自己的人生装上了外挂。\n27年程序员老兵：用AI写出多部长篇小说，一边敲代码一边圆武侠梦 ；\n硬核奶爸：手搓本地AI操作系统，把私教装进孩子口袋；\nAI安全研究员：把AI变成科研副驾，打破思维墙；\n有效加速主义者：打造AI全自动分身，让AI替自己看新闻处理琐事；\n全栈讲师：降低新手学习门槛，把技术文档自动变成PPT；\n本期视频，产品君连线5位GDE谷歌开发者专家，带你拆解AI时代的超级个体，听听他们给普通人的真诚建议。\n\n#前沿科技趋势发布月 #抖音知识年终大赏  #AI新星计划 #AI #Google",
                "cover": "https://p3-sign.douyinpic.com/tos-cn-i-dy/e8811a98fa034f85973168d834c183bd~tplv-dy-resize-walign:360:q75.jpeg?lk3s=138a59ce&x-expires=1770620400&x-signature=lTgmoJ5RXF%2BqVBoi7bu1o30Pj3c%3D&from=327834062&s=PackSourceEnum_PUBLISH&se=false&sc=cover&biz_tag=aweme_video&l=202601261530054015C224E0963CA174FB",
                "create_time": 1767098192,
                "duration": 624664,
                "item_id": "7589628862217112841",
                "link": "https://www.douyin.com/video/7589628862217112841",
                "music": {
                "music_author": "产品君",
                "music_duration": 624,
                "music_title": "@产品君创作的原声",
                "music_url": "https://sf5-hl-cdn-tos.douyinstatic.com/obj/ies-music/7589629268636863251.mp3"
                },
                "nickname": "产品君",
                "short_id": "65180295651",
                "statistics": {
                "admire_count": 0,
                "collect_count": 2491,
                "comment_count": 147,
                "digg_count": 10094,
                "download_count": 1,
                "exposure_count": 0,
                "forward_count": 0,
                "live_watch_count": 0,
                "lose_comment_count": 0,
                "lose_count": 0,
                "play_count": 0,
                "share_count": 535,
                "whatsapp_share_count": 0
                },
                "title": "抖音前沿科技30X30｜采访AI超级个体 Gemini 3发布后，这5个开发者给自己的人生装上了外挂。\n27年程序员老兵：用AI写出多部长篇小说，一边敲代码一边圆武侠梦 ；\n硬核奶爸：手搓本地AI操作系统，把私教装进孩子口袋；\nAI安全研究员：把AI变成科研副驾，打破思维墙；\n有效加速主义者：打造AI全自动分身，让AI替自己看新闻处理琐事；\n全栈讲师：降低新手学习门槛，把技术文档自动变成PPT；\n本期视频，产品君连线5位GDE谷歌开发者专家，带你拆解AI时代的超级个体，听听他们给普通人的真诚建议。 \n#前沿科技趋势发布月 #抖音知识年终大赏  #AI新星计划 #AI #Google",
                "unique_id": "aipmgo",
                "video_download_addr": "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d59s9mnog65o6br9gt10&line=1&file_id=bc4221c4b9cd4091b3809b6fc4286036&sign=73479d72c8d3e7988751123fffd8c7e2&is_play_url=1&source=PackSourceEnum_PUBLISH"
            },
            {
                "avatar": "https://p3.douyinpic.com/aweme-avatar/tos-cn-avt-0015_ac94673e8aea988adce96b9ae4c25c9f~tplv-dy-shrink-adapter:144:144.heic?from=327834062",
                "caption": "开源视频制作Remotion Skills爆火\nAI编程开无限画布插件Pencil 爆火\n开源个人AI助手Clawdbot爆火，7成24小时给你打工\nClaude Excel插件更新\nRunway上线最强视频模型Gen 4.5\n字节开源视频参考模型OminiTransfer\n字节发布最强数字人直播模型FlowACT R1\n阿里开源最强文本转语音模型Qwen 3 TTS\n\n#AI新星计划 #抖音知识年终大赏  #AI #OpenAI #AIGC",
                "cover": "https://p26-sign.douyinpic.com/tos-cn-i-dy/a91f8ecc865e4e90bef58b3639b24a3c~tplv-dy-resize-walign:360:q75.jpeg?lk3s=138a59ce&x-expires=1770620400&x-signature=DV%2FtwuCiZr2rNMAYNFav1%2B5ylTY%3D&from=327834062&s=PackSourceEnum_PUBLISH&se=false&sc=cover&biz_tag=aweme_video&l=202601261530054015C224E0963CA174FB",
                "create_time": 1769348407,
                "duration": 140459,
                "item_id": "7599293185763855667",
                "link": "https://www.douyin.com/video/7599293185763855667",
                "music": {
                "music_author": "产品君",
                "music_duration": 140,
                "music_title": "@产品君创作的原声",
                "music_url": "https://sf5-hl-cdn-tos.douyinstatic.com/obj/ies-music/7599293579936221995.mp3"
                },
                "nickname": "产品君",
                "short_id": "65180295651",
                "statistics": {
                "admire_count": 0,
                "collect_count": 6846,
                "comment_count": 252,
                "digg_count": 10375,
                "download_count": 0,
                "exposure_count": 0,
                "forward_count": 0,
                "live_watch_count": 0,
                "lose_comment_count": 0,
                "lose_count": 0,
                "play_count": 0,
                "share_count": 2427,
                "whatsapp_share_count": 0
                },
                "title": "盘点一周AI大事(1月25日)｜Agent进化，24小时打工 开源视频制作Remotion Skills爆火\nAI编程开无限画布插件Pencil 爆火\n开源个人AI助手Clawdbot爆火，7成24小时给你打工\nClaude Excel插件更新\nRunway上线最强视频模型Gen 4.5\n字节开源视频参考模型OminiTransfer\n字节发布最强数字人直播模型FlowACT R1\n阿里开源最强文本转语音模型Qwen 3 TTS \n#AI新星计划 #抖音知识年终大赏  #AI #OpenAI #AIGC",
                "unique_id": "aipmgo",
                "video_download_addr": "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d5r1jkvog65i5t3brplg&line=1&file_id=1d9f92592313428dbeff9f48524f0844&sign=942b7c96da4efc50e8381fca2d5932a8&is_play_url=1&source=PackSourceEnum_PUBLISH"
            }
            ],
            "max_cursor": 1769348407000,
            "video_download_addr_array": [
            "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d59s9mnog65o6br9gt10&line=1&file_id=bc4221c4b9cd4091b3809b6fc4286036&sign=73479d72c8d3e7988751123fffd8c7e2&is_play_url=1&source=PackSourceEnum_PUBLISH",
            "https://api.amemv.com/aweme/v1/play/?video_id=v0200fg10000d5r1jkvog65i5t3brplg&line=1&file_id=1d9f92592313428dbeff9f48524f0844&sign=942b7c96da4efc50e8381fca2d5932a8&is_play_url=1&source=PackSourceEnum_PUBLISH"
            ]
        },
        "success": true,
        "tips": "前往【https://zyunaigc.com/plugins】访问插件详情"
    }
    """
    api_token = "sat_w1VbqSIHPxn3XkDiFhRuvpjlHHmlHGg78gHEr0uU4aMDEO6RX1ccMS98UPArBiiG"
    workflow_id = "7599486351155494954"
    data = {
        "count": int(count),
        "max_cursor": int(max_cursor),
        "input": input_url
        or "https://www.douyin.com/user/MS4wLjABAAAAVmG_pTXp3pvTEwF7Cm3te2-s_RDjXsCMf3n4sgs-63u-0xRsmvBdm6gj3rjNKaR-?from_tab_name=main",
    }  # "产品君"账号的抖音视频链接
    result = run_workflow_by_cozepy(api_token, workflow_id, data)
    
    return result

# 获取视频文案
def get_video_content(video_url: str):
    """
    返回视频文案数据示例    
    {
        "code": 200,
        "ka_info": {
            "first_login_date_jifen": "2026-01-26 14:33:20",
            "key": "hf_53a43135cb37f48063a6d1cd9b47d538300",
            "remaining": 300,
            "total_points": 300,
            "used_points": 0
        },
        "msg": "提取成功",
        "transcripts": [
            {
                "text": "jamie三诞生后，全世界的开发者就像装上了外挂，做出很多离谱的应用。这些最会玩ai的人是怎么用jamie三把脑洞落地？ai又如何重构了他们的人生轨迹？对我们普通人有哪些启发和建议？大家好，我是陈敏俊，感谢抖音科技邀请google帮忙组局，今天我们连线五位google开发者专家，一起拆解ai时代的超级队。有请嘉宾陈一鱼。请介绍一下自己。大家好，我是东东，我是一名全自然工程师，也是一位ai创业者，同时还是两只猫的铲屎官。请介绍一下你开发的产品，以及为什么要做这个产品。其实我作为一个开源供应者和讲师，所以我经常会要去各地做一些分享，但是一些比如说传统的我们那些技术文档，对于小白和数学来说非常劝退，所以我做了一个appt的工具啊，目前名字还没取得特别好，就叫appt，把难懂的那个文档呢，可以翻译成通俗易懂，同文并茂的ppt。下面南山在开发的过程中起到什么样的作用？他是一个内容编辑家、设计师，他做信息整合的能力非常强，能够很快速的抓到核心的论点和关键数据，然后他也有很强的一些审美，就可以生成很现代风，就是设计感非常强的。ppt中ai开发踩过哪些坑？有没有踩坑经验可以分享一下？我的经验就是说不要试图用一个promise解决所有的问题，我会把给ai分配的工作拆系说，我会把生成app的步骤拆成先。把我输入的信息做一个规整，然后再把信息做一个排版，每一页pp展示什么样的内容，然后在排版里面再申请配图，让ai一步步的解决，并且提供足够多的一些上下文的信息，这样它的生成效果就会比较好。大家好，我是朱涛，曾经是一名大厂程序员，现在是一名ai独立开发者，同时我也是一名孩子的爸爸。作为一名父亲，我不想看到将来的ai形成一道铁幕，将人呐无情的分为掌握ai的超级个体和被甩下的局外人。这个理念呢，催生了小孩ai，它不仅仅是一个聊天框，更是一个免费的本地ai操作系统。你可以像安装app一样使用各种ai小程序，比如你可以让他帮你整理凌乱的电脑桌面，或者呢，化身成为耐心的私教，陪你练习英语口语。ai很容易在高度复杂的逻辑中一本正经的胡说八道，我自己总结了两个技巧。第一个技巧就是不要只给ai一个代码片段，要给他架构图，设计原则，还有api文档。第二个技巧是让ai先写测试，用力再写代码，既然他写得快，我们就让他自己验证自己。大家好，我是段新华，我是一名ai工程师，我也是一个有效加速主义者，我相信科技能让人类世界加速进步。我发现我每天都花大量的时间做很多重复的事情，比如说看各种ai的新闻，监控各种系统和账户的变化。想做一个ai原声的工作平台，它的名字叫chino。它能智能的帮我做一些零散又高频的事情，可以按时间、按条件或者某种事件自动出发执行，汇总成我想要的一个结果，用最小干扰的方式融入我的工作和生活。整个chino的本体呢，都是由ai完全实现的。同时呢，它也是chino里面的通用大脑，是能理解我的目标、拆解步骤，像搭积木一样持续生产出新的工具和执行工作流。我采过的一个最有意思的坑是，某个顶级的大模型至今仍不能输出中文。的双眼。大家好，我是汪志成，是一位有二十七年开发经验的软件工程师，同时也是一位热爱文学的文艺青年。很多人心中都住着一个武侠梦，梦里有一个仗剑天涯的江湖，我也一样。于是我基于詹米仔三开发了一个ai辅助创作工具，并且使用它完成了多部科幻、武侠、科普等小说的创作。最近，我用它写了一部五十万字的长篇小说绝对实现，又有趣又深刻。其灵感来自于一个都市传说，就是雍和宫。许愿必定实现，但总是有意想不到的方式和代价。这个小说创作工具的核心是是demonacri，它是一个非常强大的智能体，不仅能用于web coding，还能用于web创作。在创作过程中，最大的难点其实是创意，因为从原理上来说，ai总会朝着概率最大的方向前进，因为它是概率模型。那么如果我们不加以引导呢，ai作品就必然会走向平庸。所以每个章节我都会做人工反馈，告诉他哪段跑偏了，哪里需要。添加冲突让情节更丰富，哪里需要留白，留出思考的空间。说到底，ai只是工具，作者的创作功底和鉴赏水平才是一个文学作品的重要的底色。哈喽，大家好，我是朱小虎，是一名人工智能行业的科研工作者，也是一名连续创业者。我自己的研究方向是如何构建安全优先的通用人工智能。我在日常的科研工作中发现和ai助手往往会在模型的能力极限上卡住，无法从多角度来挖掘问题。所以我开发了nexus research这样一个产品，是一个自主的科研工具。它可以从拆体检索、交叉验证，还有多视角的推演，以及到结构化的输出，让我能够用更短的时间获得更高质量的输出和启发。洁面奶三模型作为nexus research智能体的基座，它有真正的原生多模态的能力，能够把文字、图片、视频、表格以及链接信息放在一起，综合去做推演。它还可以主动去串联一些工具，可以把任务推进到可以交付的程度。有没有被ai震撼到的时刻？有很多的惊艳的地方，其实是自己的想法被完全规模化和自动化，它能够帮你跑出来一些你自己都没有想到，但是又很合理的一些方向。那这个瞬间其实会让人眼前一亮。女儿写了一本以她为主角的数学奇幻小说，并且印刷出来作为生日礼物送给她，大家可以看一下。这个虽然不算很精美，但是胜在全世界独此一份。她拿到实体书时的那份惊喜，以及读完书之后对数学热情的提升。这就是ai带给我的幸福。你的人生因为ai产生过哪些变化？我起初是为了照顾父母，回到了我老家温州，然后我一度因为工作生活陷入一些焦虑吧，因为可能工作上面的落差比较大，然后但是呢，我发现其实身边有大量的企业和个人依然在困在一些繁琐的、机械的一些重复劳动当中，然后ai呢，就会让我成为那个造梯子的人。我想用ai下沉到一些比较具象的且有价值的一些场景上面，帮助普通人找到和ai共存的舒适区。作为一个有效加速主义者，我的人生目标呢，一直是提高这个世界的生产力。以前用科技如何帮助世界是一个很宏大也很抽象的一个事情，ai产生了之后，这件事情突然变得很具体了。ai是给所有人的生产力外挂，而我只需要把ai做得更好，更顺手，更能落地，更和每个人离得更近，就等于给每个人进行了一个加速改变事件。不一定要成为一个发明家，也可以成为发明家的倍增器。以前我是大厂的一颗焦虑的螺丝钉，a i的出现让螺丝钉更容易被替代。现在我是一名从容的独立开发者，a i成了我的外挂，我的能力边界被无限的放大，我从一个马农变成了一个产品的创造者。我想看看一个被a i武装到牙齿的超级个体到底能跑多远。以前我内心有千万种想法，但是苦于精力有限，无法去一一实现。本来我是想等退休了好。好，写小说去，没想到现在就能做到一边写程序，一边写小说。小时候的梦想告诫现实一方面非常焦虑，因为现在ai能力越来越强，进化的速度越来越快。另外一方面也会觉得非常的兴奋，因为ai在规模化一切可以被验证的任务上是非常的强势，它有机会彻底改写人类社会中的各种难题，比如说医疗、化学、物理、数学等等领域。对于我一个rntp这样的人来说，其实ai它像一个盲盒，每次打开你都可以看到新的这个世界，这种快乐是非常真实的。当然呢，这个过程也非常的烧钱。a i对你而言究竟意味着什么？对我而言，a i是我的梦想加速器。对我来说，a i是一个放大器，也是一个解放者。a i是撬动人生的阿基米德支点。a i就是我的脑力放大器，就像x教授的脑波放大机一样。a i是我们的一群共同成长朋友。对于ai，我们其实要保持一定的尊重，要不然哪一天他突然觉醒了，那就不好交代了。虽然这个是一个玩笑，但我认为这并不是不可能发生的。我自己的判断，其实可能在五到十年内，我们大概率会进入ai觉醒的阶段。如果agi到来了，你会害怕被替代吗？我不害怕被替代，我非常期待agi来到来。世界上不缺乏生存内容的机器，缺的是定义什么是好的内容的灵魂。说实话，我不害怕ai，我只害怕我自己停止学习，停止成长。你不妨想象一下，假设ai学会了人类所有的知识，那么他会做出什么样的推论呢？会如何看待我们人类呢？今天我们对待弱者的方式，就是明天agi对待弱者的方式。agi眼里的弱者是谁呢？是全体人类，无一例外。最后一个问题，对于想用好ai的普通人，你有哪些建议？很多人对ai的态度都是等等在学。我觉得ai并不是学会了再用，而是用着用着就会了。我的建议是不要做时代的旁观者，现在你可以立即打开gemini去试一下，做一个你以前觉得我不行的事情，打破你对自己设定的局限，这才是ai给你最好的礼物。我觉得现在就去用a i，如果你不会用a i，就让a i教你如何使用a i。这个人提示非常好，就比如说我不知道问什么的时候，我就直接说我需要你怎么问你。用a i驾驭a i，用魔法打扮魔法，这其实也是一个很好的学习方法。多去体验生活，多去做一些冥想，去挖掘物理俱深的优势和情感，找到自己真正感兴趣的一些方向。在这个基础之上，你再去多去用ai，看看哪一些感兴趣的事情能够用ai去加速。还记得年少时的梦吗？请找到那份属于你自己的独特性，它是蕴藏着无限可能性的种子。恋爱只是阳光和泥土，但必须有那颗种子，才能开出那朵永不凋零的花。感谢你看到这里，如果你觉得有收获，请帮我点个赞如。果你喜欢这种对谈的形式，评论区告诉我，我会去找更多的大咖来分享。我是产品君，下期再见！"
            }
        ]
    }
    """
    api_token = "sat_w1VbqSIHPxn3XkDiFhRuvpjlHHmlHGg78gHEr0uU4aMDEO6RX1ccMS98UPArBiiG"
    workflow_id = "7599546531909255177"
    data = {
        "input": video_url
    }  # "产品君"账号的抖音视频链接
    result = run_workflow_by_cozepy(api_token, workflow_id, data)
    return result

import datetime

def timestamp_to_readable(ts):
    # UTC 时间
    utc_time = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    # 本地时间
    local_time = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    return utc_time, local_time

if __name__ == "__main__":
    # ts = 1767098192
    # ts = 1769348407
    # utc, local = timestamp_to_readable(ts)
    # print("UTC 时间：", utc)
    # print("本地时间：", local)

    # print(get_video_list())
    print(get_video_content("https://www.douyin.com/video/7575911757768674569"))
    pass