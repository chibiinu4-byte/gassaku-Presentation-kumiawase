import streamlit as st
import pulp
import itertools
from collections import defaultdict
import re

st.set_page_config(page_title="発表組み合わせを作る", layout="wide")
st.title("発表組み合わせを作る")
st.markdown("もうさっき聞いた……という発表をなくします。第1グループには一回目の発表班を書いてください。もし資料を合作しているなら、第2グループに合作班を書いてください。")

# -------------------- 入力エリア --------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("第1グループ（一回目の発表班）")
    g1_text = st.text_area(
        "例：① 田中 鈴木 佐藤 高橋",
        height=300,
        placeholder="""① 田中 鈴木 佐藤 高橋
② 伊藤 渡辺 山本 中村
③ 小林 加藤 吉田 山田
④ 松本 井上 木村 林
⑤ 斎藤 清水 山口 森
⑥ 池田 橋本 石川 前田
⑦ 藤原 岡田 長谷川 近藤
⑧ 坂本 村上 石田 原田"""
    )

with col2:
    st.subheader("第2グループ（合作班・任意）")
    g2_text = st.text_area(
        "入力しなくても計算できます（合作している場合のみ記入）",
        height=300,
        placeholder="""（任意）
① 田中 伊藤
② 鈴木 渡辺
③ 佐藤 山本
..."""
    )

# -------------------- パース関数（人名対応） --------------------
def parse_groups(text):
    groups = []
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # ①②や数字を除去
        line = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳\d]+[\.．、\s]*', '', line)
        # 全角英数字を半角に
        line = line.translate(str.maketrans(
            'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅ０１２３４５６７８９',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcde0123456789'
        ))
        # 空白・読点などで分割
        symbols = re.split(r'[\s　,、]+', line)
        symbols = [s.strip() for s in symbols if s.strip()]
        if symbols:
            groups.append(set(symbols))
    return groups

# -------------------- メイン処理 --------------------
if st.button("第3グループを計算する", type="primary"):
    if not g1_text.strip():
        st.error("第1グループは必ず入力してください。")
        st.stop()

    with st.spinner("計算中...（数秒〜十数秒かかることがあります）"):
        G1 = parse_groups(g1_text)
        G2 = parse_groups(g2_text) if g2_text.strip() else []
        has_g2 = len(G2) > 0

        if not G1:
            st.error("第1グループの解析に失敗しました。入力形式を確認してください。")
            st.stop()

        if has_g2:
            symbols_g1 = set().union(*G1)
            symbols_g2 = set().union(*G2)
            if symbols_g1 != symbols_g2:
                st.error(f"第1グループと第2グループの記号（人名）が一致しません。\n"
                         f"第1のみ: {sorted(symbols_g1 - symbols_g2)}\n"
                         f"第2のみ: {sorted(symbols_g2 - symbols_g1)}")
                st.stop()
            symbols = sorted(symbols_g1)
        else:
            symbols = sorted(set().union(*G1))

        n = len(symbols)

        if n % 4 == 3:
            num4 = (n - 3) // 4
            num3 = 1
        elif n % 4 == 0:
            num4 = n // 4
            num3 = 0
        else:
            st.error(f"人数が {n} 人です。4の倍数または 4の倍数+3 になるようにしてください。")
            st.stop()

        st.info(f"人数: {n}人　→　4人班 {num4} 個 ＋ 3人班 {num3} 個 で分割します")

        # 属性関連
        if has_g2:
            attr = {}
            for i, block in enumerate(G2, 1):
                for s in block:
                    attr[s] = i

            forbidden_attr = []
            for block in G1:
                a_set = frozenset(attr[p] for p in block)
                forbidden_attr.append(a_set)

            g1_comp = {}
            for block in G1:
                for p in block:
                    g1_comp[p] = block - {p}

            attr_to_syms = defaultdict(list)
            for s, a in attr.items():
                attr_to_syms[a].append(s)

            forbidden_pairs = set()
            for a, syms in attr_to_syms.items():
                if len(syms) < 2:
                    continue
                for Y, Z in itertools.permutations(syms, 2):
                    for X in g1_comp.get(Y, []):
                        forbidden_pairs.add(frozenset([X, Z]))
        else:
            attr = {}
            forbidden_attr = []
            forbidden_pairs = set()

        def is_good(S):
            Sset = set(S)
            if has_g2:
                for B in G2:
                    if len(Sset & B) > 1:
                        return False
                a_set = frozenset(attr[p] for p in S)
                if a_set in forbidden_attr:
                    return False
                for pair in itertools.combinations(S, 2):
                    if frozenset(pair) in forbidden_pairs:
                        return False
            return True

        cand4 = [frozenset(c) for c in itertools.combinations(symbols, 4) if is_good(c)]
        cand3 = [frozenset(c) for c in itertools.combinations(symbols, 3) if is_good(c)] if num3 else []

        def overlap_cost(S):
            cost = 0
            Sset = set(S)
            for B in G1:
                inter = len(Sset & B)
                if inter > 1:
                    cost += (inter - 1)
            return cost

        costs4 = [overlap_cost(c) for c in cand4]
        costs3 = [overlap_cost(c) for c in cand3]

        # ILP
        prob = pulp.LpProblem("Third_Group", pulp.LpMinimize)
        v4 = pulp.LpVariable.dicts("B4", range(len(cand4)), cat="Binary")
        v3 = pulp.LpVariable.dicts("B3", range(len(cand3)), cat="Binary") if num3 else {}

        prob += pulp.lpSum(costs4[i] * v4[i] for i in range(len(cand4))) + \
                pulp.lpSum(costs3[i] * v3[i] for i in range(len(cand3)))

        prob += pulp.lpSum(v4[i] for i in range(len(cand4))) == num4
        if num3:
            prob += pulp.lpSum(v3[i] for i in range(len(cand3))) == num3

        for s in symbols:
            covering = [v4[i] for i, c in enumerate(cand4) if s in c]
            if num3:
                covering += [v3[i] for i, c in enumerate(cand3) if s in c]
            prob += pulp.lpSum(covering) == 1

        status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=120))

        if pulp.LpStatus[status] != "Optimal":
            st.error("条件を完全に満たす組み合わせが見つかりませんでした。入力を確認するか、人数を調整してください。")
            st.stop()

        selected = []
        for i in range(len(cand4)):
            if v4[i].varValue > 0.5:
                selected.append(sorted(cand4[i]))
        if num3:
            for i in range(len(cand3)):
                if v3[i].varValue > 0.5:
                    selected.append(sorted(cand3[i]))

        circled = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
        result_lines = []
        for idx, block in enumerate(selected):
            num = circled[idx] if idx < len(circled) else f"{idx+1}."
            result_lines.append(f"{num}{' '.join(block)}")

        st.success("計算完了！")
        st.subheader("第3グループ（新しい発表班）")
        st.code("\n".join(result_lines), language=None)

        with st.expander("詳細情報（検証用）"):
            st.write(f"総オーバーラップコスト（小さいほど良い）: {int(pulp.value(prob.objective))}")
            if has_g2:
                st.write("各班の属性組み合わせ:")
                for block in selected:
                    a_set = sorted(attr[p] for p in block)
                    st.write(f"{' '.join(block)} → {a_set}")

st.markdown("---")
st.caption("「発表組み合わせを作る」｜もうさっき聞いた発表をなくすツール")
