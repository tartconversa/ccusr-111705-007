"""银发商圈的辅助服务可达性巡查：目录卡片既有数据约定与巡查判定。"""
import re

PENDING_DAY = '时段待公布'
UNKNOWN_SLOT = 'unknown_slot'
UNKNOWN_ELIGIBILITY = 'unknown_eligibility'
TERMS_UNCONFIRMED = 'terms_unconfirmed'
TERMS_MISMATCH = 'keyboard_terms_mismatch'
FOCUS_BLOCKED = 'dialog_focus_blocked'
DIALOG_NOT_OPENED = 'dialog_not_opened'
REACHABLE = 'reachable'
BLOCKED = 'keyboard_blocked'
PARTIAL = 'partially_reachable'


def interpret_card(item):
    parts = item['summary'].split(' · ', 1)
    if len(parts) != 2:
        raise ValueError('卡片摘要格式无效')
    condition, observation = parts
    found = re.fullmatch(r"(?P<amount>周[一二三四五六日])开放", observation)
    if not found:
        raise ValueError('卡片状态未识别')
    amount = found.group('amount')
    return {'kind': 'assistance', 'identity': item['id'], 'condition': condition, 'hours': observation, 'weekday': int(amount) if amount.isdigit() else amount}

def interpret_entry(catalog_fact, signal):
    if signal['service'] != catalog_fact['identity'] or not signal['service_day']:
        raise ValueError('service floor mismatch')
    return {'business_key': f"{signal['service']}:{signal['floor']}:{signal['service_day']}", 'floor': signal['floor'], 'service_day': signal['service_day']}


def is_pending_day(service_day):
    """目录或页面文字只显示“时段待公布”时，资格/时段属于未知而非不可达。"""
    return bool(service_day) and PENDING_DAY in service_day


def floor_business_key(item_id, floor, service_day):
    """同名服务在不同楼层生成不同业务键，禁止跨楼层合并。"""
    return f'{item_id}:{floor}:{service_day}'


def build_verdict(observed):
    """由巡查观察生成只读结论。observed 为单楼层单服务的观察字典。

    结论只描述真实可达条件：哪一步键盘交互阻断、资格或时段为何未知，
    不把鼠标路径的成功当作键盘路径成功，也不把预约预览当作已提交预约。
    """
    unknown = []
    keyboard_blocked_step = None

    if is_pending_day(observed['service_day']):
        unknown.append(UNKNOWN_SLOT)
    if not observed.get('mouse', {}).get('opened'):
        unknown.append(UNKNOWN_ELIGIBILITY)
    elif not observed.get('keyboard', {}).get('opened'):
        keyboard_blocked_step = DIALOG_NOT_OPENED
    else:
        if not observed['keyboard'].get('focus_inside'):
            keyboard_blocked_step = FOCUS_BLOCKED
        mouse_text = observed['mouse'].get('terms_text') or ''
        keyboard_text = observed['keyboard'].get('terms_text') or ''
        if mouse_text and keyboard_text and mouse_text != keyboard_text:
            keyboard_blocked_step = keyboard_blocked_step or TERMS_MISMATCH
            unknown.append(TERMS_MISMATCH)
        if not keyboard_text:
            unknown.append(UNKNOWN_ELIGIBILITY)

    if observed.get('preview', {}).get('state') == 'terms_unconfirmed':
        unknown.append(TERMS_UNCONFIRMED)
    elif observed.get('preview', {}).get('state') in ('unavailable', 'not_observed'):
        unknown.append(UNKNOWN_ELIGIBILITY)

    if keyboard_blocked_step and UNKNOWN_SLOT not in unknown:
        reachability = BLOCKED
    elif keyboard_blocked_step or unknown:
        reachability = PARTIAL
    else:
        reachability = REACHABLE
    return {
        'reachability': reachability,
        'unknown': sorted(set(unknown)),
        'keyboard_blocked_step': keyboard_blocked_step,
        'preview_state': observed.get('preview', {}).get('state', 'not_observed'),
        'booking_submitted': False,
    }
