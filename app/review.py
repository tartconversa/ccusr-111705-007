"""只审阅已观察的详情入口，不把候选记录当作已完成的业务。"""

UNKNOWN_LABELS = {
    'unknown_slot': '服务时段未知（页面显示时段待公布）',
    'unknown_eligibility': '体验资格或服务说明未知',
    'terms_unconfirmed': '预约前未核对本楼层服务说明',
    'keyboard_terms_mismatch': '键盘与鼠标打开的服务说明文本不一致',
}
BLOCK_LABELS = {
    'dialog_not_opened': '键盘无法打开服务说明弹窗',
    'dialog_focus_blocked': '弹窗已打开但键盘焦点未进入弹窗',
    'keyboard_terms_mismatch': '键盘路径读到的服务说明与鼠标路径不同',
}
REACHABILITY_LABELS = {
    'reachable': '键盘与鼠标均可完整核对体验条件',
    'partially_reachable': '部分条件未知，需人工再核对',
    'keyboard_blocked': '键盘交互阻断，老人无法独立完成核对',
}
PREVIEW_LABELS = {
    'confirmed_preview': '预约预览显示服务说明已核对（仅预览，未提交）',
    'terms_unconfirmed': '预约预览提示说明待核对',
    'unavailable': '资格或时段未知，暂不可核对预约',
    'not_observed': '预约预览未取得有效内容',
}


def review_entries(entries):
    accessibility = []
    for entry in entries:
        detail = entry['detail_fact']
        accessibility.append({'service_floor': detail['business_key'], 'service_day': detail['service_day'],
                              'keyboard_path': 'not_observed', 'booking': 'unconfirmed'})
    return accessibility


def summarize_access_reviews(reviews):
    """把逐楼层巡查观察转成志愿者替老人核对时可直接使用的结论清单。"""
    summary = []
    for review in reviews:
        verdict = review['verdict']
        unknowns = [UNKNOWN_LABELS.get(code, code) for code in verdict['unknown']]
        blocked = verdict['keyboard_blocked_step']
        summary.append({
            'service': review['name'],
            'item_id': review['item_id'],
            'floor': review['floor'],
            'business_key': review['business_key'],
            'service_day': review['floor_filter']['service_day'],
            'reachability': verdict['reachability'],
            'reachability_note': REACHABILITY_LABELS.get(verdict['reachability'], verdict['reachability']),
            'keyboard_blocked_step': blocked,
            'keyboard_blocked_note': BLOCK_LABELS.get(blocked) if blocked else None,
            'unknown_conditions': unknowns,
            'preview_note': PREVIEW_LABELS.get(verdict['preview_state'], verdict['preview_state']),
            'booking_submitted': False,
        })
    return summary
