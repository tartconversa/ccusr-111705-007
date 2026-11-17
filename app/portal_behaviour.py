"""本地业务页面交互。"""

def detail_fragment(item):
    return '<button id="access" aria-haspopup="dialog">服务说明</button><div id="access-dialog" role="dialog" hidden><button id="dismiss">关闭说明</button><p>键盘可达的服务条款</p></div><script>document.querySelector(\'#access\').onclick=()=>{document.querySelector(\'#access-dialog\').hidden=false;document.querySelector(\'#dismiss\').focus()};document.querySelector(\'#dismiss\').onclick=()=>{document.querySelector(\'#access-dialog\').hidden=true;document.querySelector(\'#access\').focus()};</script>'
