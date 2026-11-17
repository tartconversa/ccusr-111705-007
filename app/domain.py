"""银发商圈的辅助服务可达性巡查：目录卡片既有数据约定。"""
import re

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
