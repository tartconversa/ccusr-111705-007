"""本地业务页面交互。

楼层、服务日和服务说明均由 fixture 数据驱动。部分服务存在真实演练缺陷：
- `keyboard_defect`：键盘打开弹窗时焦点不进入弹窗，且键盘与鼠标看到的说明文本不同；
- 楼层 `service_day` 为“时段待公布”时，预约预览只能给出时段未知结论。
"""
import json

PENDING_DAY = '时段待公布'
DEFAULT_FLOORS = [
    {'floor': '一层', 'service_day': '周二开放'},
    {'floor': '二层', 'service_day': '周四开放'},
]
DEFAULT_TERMS = '键盘可达的服务条款'


def _floors(item):
    return item.get('floors') or DEFAULT_FLOORS


def _terms(item):
    return item.get('service_terms') or DEFAULT_TERMS


def detail_fragment(item):
    rows = _floors(item)
    options = ''.join(
        f'<option value="{row["floor"]}">{row["floor"]}</option>' for row in rows
    )
    days = json.dumps({row['floor']: row['service_day'] for row in rows}, ensure_ascii=False)
    terms = _terms(item)
    terms_map = json.dumps(
        terms if isinstance(terms, dict) else {'mouse': terms, 'keyboard': terms},
        ensure_ascii=False,
    )
    defect = 'true' if item.get('keyboard_defect') else 'false'
    initial_day = rows[0]['service_day']
    return (
        '<button id="access" aria-haspopup="dialog">服务说明</button>'
        '<div id="access-dialog" role="dialog" hidden>'
        '<button id="dismiss">关闭说明</button>'
        '<p id="access-terms"></p></div>'
        f'<select id="floor">{options}</select>'
        f'<output id="service-day">{initial_day}</output>'
        '<script>(()=>{'
        'let floor=document.querySelector("#floor"),'
        'dialog=document.querySelector("#access-dialog"),'
        'access=document.querySelector("#access"),'
        'terms=document.querySelector("#access-terms"),'
        f'days={days},termMap={terms_map},defect={defect};'
        'floor.onchange=()=>{dialog.hidden=true;terms.textContent="";'
        'document.querySelector("#service-day").textContent=days[floor.value];};'
        'access.onclick=(event)=>{'
        'let viaKeyboard=event.detail===0;'
        'terms.textContent=viaKeyboard?termMap.keyboard:termMap.mouse;'
        'dialog.hidden=false;'
        'if(defect&&viaKeyboard){access.focus();}else{document.querySelector("#dismiss").focus();}'
        '};'
        'document.querySelector("#dismiss").onclick=()=>{dialog.hidden=true;access.focus();};'
        '})();</script>'
    )


def source_extension(item):
    rows = _floors(item)
    days = json.dumps({row['floor']: row['service_day'] for row in rows}, ensure_ascii=False)
    return f"""<output id="assistance-preview" data-service="{item['id']}"></output><script>(()=>{{
let assistance=document.querySelector('#assistance-preview'),floor=document.querySelector('#floor'),dialog=document.querySelector('#access-dialog'),days={days};
let viewedFloor='';floor.addEventListener('change',()=>{{assistance.textContent='';viewedFloor='';}});
document.querySelector('#access').addEventListener('click',()=>{{viewedFloor=floor.value;}});
document.querySelector('#preview').addEventListener('click',()=>{{
let day=days[floor.value];
if(day==={json.dumps(PENDING_DAY, ensure_ascii=False)}){{assistance.textContent=floor.value+' / '+day+'：资格或时段未知，暂不可核对预约';return;}}
assistance.textContent=floor.value+' / '+day+'：'+(viewedFloor===floor.value?'服务说明已打开':'说明待核对');
}});
}})();</script>"""
