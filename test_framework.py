#!/usr/bin/env python3
"""
全项目路由拉通测试框架
- 逐步测试，每接口间隔 delay_ms
- 遇到限流（code 429 / 403 rate limit）自动重试
- 每个接口返回值写入 MD 文档
"""
import sys, time, json, os, traceback
sys.path.insert(0, '.')

DELAY_MS = 500  # 默认 500ms 间隔
MAX_RETRY = 5
OUTPUT_DIR = '/root/.openclaw/test/saas_tenant_skill-master/test_results'

os.makedirs(OUTPUT_DIR, exist_ok=True)

all_results = []  # [(name, code, message, data_excerpt)]

def delay():
    time.sleep(DELAY_MS / 1000.0)

def test(name, func, *args, **kwargs):
    """
    测试一个接口，自动重试限流
    """
    for attempt in range(MAX_RETRY):
        delay()
        try:
            r = func(*args, **kwargs)
            if isinstance(r, dict):
                code = r.get('code', -1)
                msg = r.get('message', '')
                # 判断是否限流
                if code in (429, 403, -1) and any(k in str(msg).lower() for k in ['rate', 'limit', '限流', '频繁', 'too many']):
                    wait = 5 * (attempt + 1)
                    print(f"  ⏳ {name}: 触发限流，等待 {wait}s 后重试 ({attempt+1}/{MAX_RETRY})...")
                    time.sleep(wait)
                    continue
                all_results.append((name, code, msg, r.get('data')))
                status = "✅" if code == 0 else "❌"
                print(f"  {status} {name}: code={code}, {str(msg)[:60]}")
                return r
            else:
                all_results.append((name, -3, f"返回类型异常: {type(r)}", None))
                print(f"  ❌ {name}: 返回类型异常 {type(r)}")
                return r
        except Exception as e:
            err = str(e)
            if any(k in err.lower() for k in ['rate', 'limit', '429', '403', '限流', '频繁']):
                wait = 5 * (attempt + 1)
                print(f"  ⏳ {name}: 触发限流，等待 {wait}s 后重试 ({attempt+1}/{MAX_RETRY})...")
                time.sleep(wait)
                continue
            all_results.append((name, -2, f"EXC: {err[:100]}", None))
            print(f"  ❌ {name}: EXC {err[:80]}")
            return None
    # 重试耗尽
    all_results.append((name, -1, "重试超限流限制", None))
    print(f"  ❌ {name}: 重试超过 {MAX_RETRY} 次，跳过")
    return None

def write_md(filename, title, sections):
    """
    写入 MD 报告
    sections: [(section_name, results_list)]
    """
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"> 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        total = sum(len(s[1]) for s in sections)
        passed = sum(1 for _, rs in sections for _, c, _, _ in rs if c == 0)
        f.write(f"## 汇总\n\n")
        f.write(f"- 总接口数: **{total}**\n")
        f.write(f"- 通过数: **{passed}**\n")
        f.write(f"- 通过率: **{passed/total*100:.1f}%**\n\n")
        
        for sec_name, rs in sections:
            sec_pass = sum(1 for _, c, _, _ in rs if c == 0)
            f.write(f"- {sec_name}: {sec_pass}/{len(rs)}\n")
        
        f.write(f"\n---\n\n")
        
        for sec_name, rs in sections:
            f.write(f"## {sec_name}\n\n")
            f.write(f"| # | 接口 | 状态 | code | 消息 |\n")
            f.write(f"|:-:|:-----|:----:|:----:|:-----|\n")
            for i, (name, code, msg, data) in enumerate(rs, 1):
                status = "✅" if code == 0 else "❌"
                msg_safe = str(msg).replace('|', '\\|')[:80]
                f.write(f"| {i} | `{name}` | {status} | {code} | {msg_safe} |\n")
            f.write(f"\n")
            
            # 失败详情
            fails = [(n, c, m, d) for n, c, m, d in rs if c != 0]
            if fails:
                f.write(f"### 失败详情\n\n")
                for name, code, msg, data in fails:
                    f.write(f"#### ❌ `{name}`\n\n")
                    f.write(f"- code: `{code}`\n")
                    f.write(f"- message: `{msg}`\n")
                    if data:
                        f.write(f"- data: ```json\n{json.dumps(data, ensure_ascii=False, indent=2)[:500]}\n```\n")
                    f.write(f"\n")
        
        f.write(f"\n---\n*由拉通测试脚本自动生成*\n")
    
    return path

print(f"测试框架已加载，间隔 {DELAY_MS}ms，输出目录: {OUTPUT_DIR}")
