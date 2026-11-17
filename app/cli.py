"""公开目录采集与可达性巡查演示（只读，不提交预约）。"""
import json
import sys
from .capture import read_catalog
from .patrol import inspect_access
from .review import summarize_access_reviews

DEFAULT_ORIGIN = 'http://127.0.0.1:8765/'


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'patrol':
        result = inspect_access(DEFAULT_ORIGIN)
        print(json.dumps(summarize_access_reviews(result['records']), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(read_catalog(DEFAULT_ORIGIN), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
