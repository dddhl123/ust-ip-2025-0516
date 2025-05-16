import json
import re
import matplotlib.pyplot as plt

raw_results = ['result_5.jsonl',
               'result_7.jsonl',
               'result_12.jsonl']


def main():
    all_errors = []
    for filename in raw_results:
        relative_errors = []
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                # 匹配 'relative_error': '数字%'
                match = re.search(r"'relative_error': '([\d\.]+)%'", line)
                if match:
                    relative_error = float(match.group(1))
                    relative_errors.append(relative_error)
        all_errors.append(relative_errors)

    # 画图
    plt.figure(figsize=(10, 6))
    for i, errors in enumerate(all_errors):
        plt.plot(errors, label=f"Query {raw_results[i].split('_')[1].replace('.jsonl','')}")
    plt.xlabel('Experiment Count')
    plt.ylabel('Relative Error (%)')
    plt.title('Relative Error Comparison')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
