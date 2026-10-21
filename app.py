import streamlit as st
import pulp
import itertools
from collections import defaultdict, Counter
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
        height=280,
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
        height=280,
        placeholder="""（任意）
① 田中 伊藤
② 鈴木 渡辺
③ 佐藤 山本
..."""
    )

# 班の人数指定
st.subheader("第3グループの班の人数を指定")
size_text = st.text_input(
    "作りたい班の人数をスペース区切りで入力してください（合計が人数と一致するように）",
    value="",
    placeholder="例: 4 4 4 3 3　　または　　2 2 2 2 3 3 4　　など（2人班・3人班もOK）"
)
st.caption("空欄の場合は自動で「できるだけ4人班 + 余り」にします。2人班や3人班も自由に指定できます。")

# -------------------- パース関数（人名対応） --------------------
def parse_groups(text):
    groups = []
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳\d]+[\.．、\s]*', '', line)
        line = line.translate(str.maketrans(
            'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅ０１２３４５６７８９',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcde0123456789'
        ))
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

    with st.spinner("計算中...（人数が多いと時間がかかることがあります）"):
        G1 = parse_groups(g1_text)
        G2 = parse_groups(g2_text) if g2_text.strip() else []
        has_g2 = len(G2) > 0

        if not G1:
            st.error("第1グループの解析に失敗しました。入力形式を確認してください。")
            st.stop()

        # 第1グループの人名を基準にする
        symbols = sorted(set().union(*G1))
        n = len(symbols)

        if has_g2:
            symbols_g2 = set().union(*G2)
            only_g1 = set(symbols) - symbols_g2
            only_g2 = symbols_g2 - set(symbols)
            if only_g1:
                st.warning(f"第1グループにしかいない人名（属性制約の対象外）: {sorted(only_g1)}")
            if only_g2:
                st.warning(f"第2グループにしかいない人名（無視されます）: {sorted(only_g2)}")

        # ----- 班の人数を決定 -----
        if size_text.strip():
            try:
                sizes = [int(x) for x in size_text.strip().split()]
                if sum(sizes) != n:
                    st.error(f"指定した班の人数の合計（{sum(sizes)}）が実際の人数（{n}）と一致しません。")
                    st.stop()
                if any(s < 1 for s in sizes):
                    st.error("班の人数は1以上にしてください。")
                    st.stop()
            except ValueError:
                st.error("班の人数は数字をスペース区切りで入力してください。")
                st.stop()
        else:
            # 自動：できるだけ4人班
            num4 = n // 4
            remainder = n % 4
            if remainder == 0:
                sizes = [4] * num4
            elif remainder == 3:
                sizes = [4] * num4 + [3]
            elif remainder == 2:
                sizes = [4] * (num4 - 1) + [3, 3] if num4 >= 1 else [2]
            elif remainder == 1:
                sizes = [4] * (num4 - 1) + [3, 2] if num4 >= 1 else [1]
            else:
                sizes = [n]

        st.info(f"人数: {n}人　→　班の構成: {sizes}")

        # 属性関連（第1グループに存在する人名のみ対象）
        if has_g2:
            attr = {}
            for i, block in enumerate(G2, 1):
                for s in block:
                    if s in symbols:  # 第1グループにいるする人名だけ属性を付与
                        attr[s] = i

            forbidden_attr = []
            for block in G1:
                a_set = frozenset(attr[p] for p in block if p in attr)
                if a_set:  # 空でない場合のみ禁止リストに追加
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
                        if X in symbols:
                            forbidden_pairs.add(frozenset([X, Z]))
        else:
            attr = {}
            forbidden_attr = []
            forbidden_pairs = set()

        def is_good(S):
            Sset = set(S)
            if has_g2:
                # 第2グループとの重複 ≤1（存在する人名のみ）
                for B in G2:
                    inter = Sset & B
                    if len(inter) > 1:
                        return False
                # 属性組み合わせ禁止
                a_set = frozenset(attr[p] for p in S if p in attr)
                if a_set and a_set in forbidden_attr:
                    return False
                # 禁止ペア
                for pair in itertools.combinations(S, 2):
                    if frozenset(pair) in forbidden_pairs:
                        return False
            return True

        # サイズごとに候補を生成
        size_count = Counter(sizes)
        candidates = {}
        for size in size_count:
            candidates[size] = [frozenset(c) for c in itertools.combinations(symbols, size) if is_good(c)]

        def overlap_cost(S):
            cost = 0
            Sset = set(S)
            for B in G1:
                inter = len(Sset & B)
                if inter > 1:
                    cost += (inter - 1)
            return cost

        # ILP（PuLP 4.x対応）
        prob = pulp.LpProblem("Third_Group", pulp.LpMinimize)
        vars_dict = {}

        objective_terms = []
        for size, cands in candidates.items():
            for i, c in enumerate(cands):
                var = prob.add_variable(f"B_{size}_{i}", cat="Binary")
                vars_dict[(size, i)] = var
                objective_terms.append(overlap_cost(c) * var)

        prob += pulp.lpSum(objective_terms)

        # 各サイズの個数制約
        for size, cnt in size_count.items():
            prob += pulp.lpSum(vars_dict[(size, i)] for i in range(len(candidates[size]))) == cnt

        # 各人がちょうど1回使われる
        for s in symbols:
            covering = []
            for size, cands in candidates.items():
                for i, c in enumerate(cands):
                    if s in c:
                        covering.append(vars_dict[(size, i)])
            prob += pulp.lpSum(covering) == 1

        # ソルバー呼び出し
        stats = prob.solve(pulp.COIN_CMD(msg=False, timeLimit=180))

        if stats.status != pulp.LpSolveStatus.Optimal:
            st.error("条件を完全に満たす組み合わせが見つかりませんでした。班の人数指定を変えるか、制約を緩めてみてください。")
            st.stop()

        selected = []
        for size, cands in candidates.items():
            for i, c in enumerate(cands):
                if vars_dict[(size, i)].varValue > 0.5:
                    selected.append(sorted(c))

        # サイズの大きい順に並べ替え
        selected.sort(key=lambda x: -len(x))

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
                    a_set = sorted(attr[p] for p in block if p in attr)
                    st.write(f"{' '.join(block)} → {a_set}")

st.markdown("---")
st.caption("「発表組み合わせを作る」｜もうさっき聞いた発表をなくすツール")
