class TextDiff:
    def __init__(self, ref_file):
        with open(ref_file) as f:
            self.ref = {line.strip() for line in f}
            print(f'Loaded {len(self.ref)} reference lines from {ref_file}')
        
    def diff(self, target_file):
        with open(target_file) as f:
            return [(i, line.strip()) for i, line in enumerate(f, 1) 
                    if line.strip() not in self.ref]
    def save_diff(self, target_file, output_file="diff_result.txt"):
        missing = self.diff(target_file)
        with open(output_file, 'w') as f:
            for _, line in missing:
                f.write(f"{line}\n")

# 使用示例
if __name__ == "__main__":
    diff = TextDiff("first.txt")
    missing = diff.diff("second.txt")
    for num, line in missing:
        print(num, line)