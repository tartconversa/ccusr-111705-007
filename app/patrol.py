"""沿 目录 → 楼层筛选 → 服务说明 → 预约预览 的真实可达性巡查。

流程约束（志愿者替老人核对辅具体验条件）：
- 只用真实 Chromium 读取环回页面，记录每一步实际观察到的文本与焦点状态，
  静态卡片文字不得替代弹窗和 aria-live 异步区域的真实内容；
- 服务说明分别走鼠标与键盘两条路径，二者结果分别记录、不互相替代；
- 同名服务按楼层分别出记录，业务键含楼层与服务日，禁止跨楼层合并；
- 全程只读：不填写任何个人信息、不点击提交类控件、不发起预约，
  任何非 GET 或离开环回来源的请求都视为违规并中止。
"""
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

from .domain import (
    build_verdict,
    floor_business_key,
    interpret_card,
    is_pending_day,
    DIALOG_NOT_OPENED,
    FOCUS_BLOCKED,
)

LOOPBACK_HOSTS = ('127.0.0.1', 'localhost')
# 巡查允许触碰的控件：楼层筛选与只读说明/预览按钮。任何输入框、提交按钮都不在其中。
ALLOWED_CONTROLS = {'BUTTON', 'SELECT', 'OPTION'}


def _check_origin(origin):
    parts = urlsplit(origin)
    if parts.hostname not in LOOPBACK_HOSTS or parts.scheme != 'http':
        raise ValueError('只允许本地演练来源')


def _wait_async_text(locator, timeout=2000):
    """等待 aria-live 区域结束“读取中/核对中”占位，返回真实异步文本。"""
    try:
        locator.wait_for(state='visible', timeout=timeout)
    except Exception:
        return {'text': '', 'settled': False, 'loading_seen': False}
    loading_seen = False
    try:
        page = locator.page
        page.wait_for_function(
            '(el) => el.textContent.trim() !== "" && !el.textContent.includes("读取中") && !el.textContent.includes("核对中")',
            arg=locator.element_handle(),
            timeout=timeout,
        )
    except Exception:
        loading_seen = True
    text = locator.inner_text().strip()
    settled = bool(text) and '读取中' not in text and '核对中' not in text
    return {'text': text, 'settled': settled, 'loading_seen': loading_seen}


class _ReadOnlyGuard:
    """拦截任何提交企图与非环回请求；巡查本身只做 GET 导航。"""

    def __init__(self, context):
        self.violations = []
        self.requests = []
        context.on('request', self._on_request)

    def _on_request(self, request):
        self.requests.append({'method': request.method, 'url': request.url})
        parts = urlsplit(request.url)
        if request.method.upper() != 'GET' or parts.hostname not in LOOPBACK_HOSTS:
            self.violations.append({'method': request.method, 'url': request.url})

    def safe_click(self, page, selector):
        handle = page.locator(selector)
        info = handle.evaluate(
            'el => ({tag: el.tagName, type: el.getAttribute("type"), '
            'inForm: !!el.closest("form"), formMethod: el.closest("form") && el.closest("form").method, '
            'href: el.getAttribute("href")})'
        )
        if info['tag'] == 'A':
            # 仅允许环回来源内的 GET 导航链接；表单链接与外站链接拒绝。
            href = info['href'] or ''
            external = href.startswith(('http://', 'https://')) and urlsplit(href).hostname not in LOOPBACK_HOSTS
            if info['inForm'] or not href or external:
                raise PermissionError(f'巡查拒绝非环回或表单链接：{selector}')
            handle.click()
            return
        if info['tag'] not in ALLOWED_CONTROLS:
            raise PermissionError(f'巡查为只读流程，拒绝点击非说明控件：{selector}')
        if info['tag'] == 'BUTTON' and info['type'] not in (None, 'button'):
            raise PermissionError(f'巡查不得提交预约，拒绝点击提交控件：{selector}')
        if info['inForm'] and (info['formMethod'] or 'get').lower() != 'get':
            raise PermissionError(f'巡查不得提交表单：{selector}')
        handle.click()

    def require_clean(self):
        if self.violations:
            raise PermissionError(f'巡查过程中出现提交或越界请求：{self.violations}')


def _observe_dialog(page, guard, via):
    """观察服务说明弹窗的真实可达性；via 为 'mouse' 或 'keyboard'。"""
    dialog = page.locator('#access-dialog')
    terms = page.locator('#access-terms')
    observation = {'opened': False, 'terms_text': '', 'focus_inside': False,
                   'focused_id': '', 'dismissed': False, 'dismiss_reached': False,
                   'blocked_step': None}
    try:
        if via == 'keyboard':
            page.locator('#access').focus()
            page.keyboard.press('Enter')
        else:
            guard.safe_click(page, '#access')
        dialog.wait_for(state='visible', timeout=2000)
        observation['opened'] = True
        observation['terms_text'] = terms.inner_text().strip()
        focus = page.evaluate(
            '() => ({id: document.activeElement.id, '
            'inside: document.querySelector("#access-dialog").contains(document.activeElement)})'
        )
        observation['focused_id'] = focus['id']
        observation['focus_inside'] = focus['inside']
        if via == 'keyboard' and not focus['inside']:
            observation['blocked_step'] = FOCUS_BLOCKED

        if via == 'keyboard':
            # 只用键盘关闭：当前焦点已在关闭键则直接 Enter，否则 Tab 寻找，禁止代点鼠标。
            for _ in range(5):
                active = page.evaluate('document.activeElement.id')
                if active == 'dismiss':
                    observation['dismiss_reached'] = True
                    break
                page.keyboard.press('Tab')
            if observation['dismiss_reached']:
                page.keyboard.press('Enter')
        else:
            guard.safe_click(page, '#dismiss')
        dialog.wait_for(state='hidden', timeout=2000)
        observation['dismissed'] = True
    except Exception as exc:
        if not observation['opened']:
            observation['blocked_step'] = DIALOG_NOT_OPENED
        observation['error'] = type(exc).__name__
        # 恢复现场，避免影响后续楼层：鼠标兜底关闭弹窗（不改变键盘路径已记录的事实）。
        if dialog.count() and dialog.is_visible():
            try:
                page.locator('#dismiss').click(timeout=1000)
            except Exception:
                pass
    return observation


def _inspect_floor(page, guard, item, floor_name):
    page.locator('#floor').select_option(floor_name)
    service_day = page.locator('#service-day').inner_text().strip()
    pending = is_pending_day(service_day)

    # 异步说明面板（“键盘焦点”维度）：鼠标与键盘各触发一次，等待占位态结束。
    guard.safe_click(page, '#details')
    panel_mouse = _wait_async_text(page.locator('#panel'))
    page.locator('#details').focus()
    page.keyboard.press('Enter')
    panel_keyboard = _wait_async_text(page.locator('#panel'))

    # 预约预览①：尚未在本楼层打开服务说明，应只能得到“说明待核对”或时段未知。
    guard.safe_click(page, '#preview')
    preview_before = _wait_async_text(page.locator('#assistance-preview'))

    mouse = _observe_dialog(page, guard, 'mouse')
    # 预约预览②：鼠标核对过服务说明之后。
    guard.safe_click(page, '#preview')
    preview_after_mouse = _wait_async_text(page.locator('#assistance-preview'))

    keyboard = _observe_dialog(page, guard, 'keyboard')
    # 预约预览③：键盘路径之后，保留页面原话以便区分“显示已打开”与“键盘真的可达”。
    guard.safe_click(page, '#preview')
    preview_after_keyboard = _wait_async_text(page.locator('#assistance-preview'))

    if pending:
        preview_state = 'unavailable'
    elif '服务说明已打开' in preview_after_mouse['text']:
        preview_state = 'confirmed_preview'
    elif '说明待核对' in preview_before['text']:
        preview_state = 'terms_unconfirmed'
    else:
        preview_state = 'not_observed'

    observed = {
        'service_day': service_day,
        'mouse': mouse,
        'keyboard': keyboard,
        'preview': {'state': preview_state},
    }
    return {
        'item_id': item['id'],
        'name': item['name'],
        'floor': floor_name,
        'source': page.url,
        'business_key': floor_business_key(item['id'], floor_name, service_day),
        'catalog_fact': interpret_card(item),
        'floor_filter': {'floor': floor_name, 'service_day': service_day, 'pending_slot': pending},
        'async_panel': {'mouse': panel_mouse, 'keyboard': panel_keyboard},
        'mouse': mouse,
        'keyboard': keyboard,
        'preview': {
            'state': preview_state,
            'before_opening_terms': preview_before,
            'after_mouse_terms': preview_after_mouse,
            'after_keyboard_terms': preview_after_keyboard,
        },
        'verdict': build_verdict(observed),
    }


def _inspect_item(page, guard, item):
    card = page.locator(f'.card[data-key="{item["id"]}"]')
    if card.count() != 1:
        raise ValueError(f'目录卡片身份不唯一：{item["id"]}')
    catalog_summary = card.locator('p').inner_text().strip()
    guard.safe_click(page, f'.card[data-key="{item["id"]}"] a')
    if page.locator('main').get_attribute('data-key') != item['id']:
        raise ValueError(f'详情身份与目录不一致：{item["id"]}')

    floor_names = page.locator('#floor option').evaluate_all(
        '(nodes) => nodes.map(n => n.value)'
    )
    records = []
    for floor_name in floor_names:
        record = _inspect_floor(page, guard, item, floor_name)
        record['catalog_summary'] = catalog_summary
        records.append(record)
    page.locator('a[href="/"]').first.click()
    page.wait_for_selector('main .card')
    return records


def inspect_access(origin, item_ids=None):
    """巡查目录中各辅具体验服务在每个楼层的真实可达条件。

    返回每个“服务 × 楼层”一条记录（不合并同名服务），含原始观察与判定结论。
    """
    _check_origin(origin)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            guard = _ReadOnlyGuard(context)
            page = context.new_page()
            page.on('pageerror', lambda exc: guard.violations.append({'pageerror': str(exc)}))
            page.goto(origin, wait_until='domcontentloaded')
            if not page.locator('main').count():
                raise ValueError('来源目录未加载')

            catalog = page.locator('.card').evaluate_all(
                '(nodes) => nodes.map(n => ({id: n.dataset.key, name: n.querySelector("h2").textContent,'
                ' summary: n.querySelector("p").textContent, href: n.querySelector("a").getAttribute("href")}))'
            )
            if item_ids is not None:
                wanted = set(item_ids)
                catalog = [row for row in catalog if row['id'] in wanted]
                missing = wanted - {row['id'] for row in catalog}
                if missing:
                    raise ValueError(f'目录中不存在服务：{sorted(missing)}')

            all_records = []
            for row in catalog:
                all_records.extend(_inspect_item(page, guard, row))
            guard.require_clean()
            return {'source': origin, 'requests': guard.requests, 'records': all_records}
        finally:
            browser.close()
