import argparse
import json

from .data import load_experiment_input


def main() -> None:
    parser = argparse.ArgumentParser(description="读取并校验 DFJSP-T 实验输入")
    parser.add_argument("instance", help="Brandimarte .fjs 文件")
    parser.add_argument("resources", help="机器距离和能耗 JSON 文件")
    args = parser.parse_args()
    data = load_experiment_input(args.instance, args.resources)
    summary = data.instance.to_matlab_dict()
    summary["agv_count"] = data.agv.count
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

