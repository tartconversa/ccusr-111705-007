"""Candidate review of observed entry facts, never a completed transaction."""

def review_entries(entries):
    accessibility = []
    for entry in entries:
        detail = entry['detail_fact']
        accessibility.append({'service_floor': detail['business_key'], 'service_day': detail['service_day'],
                              'keyboard_path': 'not_observed', 'booking': 'unconfirmed'})
    return accessibility
