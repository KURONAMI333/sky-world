
## 2026-09-04 ore_strategy の参照列（surface_y / floor_y）が未決

isekai-api 側の欠陥（幅ゼロの帯が空中へ解決する）は 2.1.0 で直した
（mod-029 `5b6d5ff`。resolveY を胴体へクランプ＋潰れた帯を起動時 WARN）。
**sky.json 側の値は未確定のまま止めてある。**

### なぜ 1 つに決まらないか

`surface_y` / `floor_y` は **vanilla 側**の参照 Y であって、島の帯（Y30-78 /
116-176 / 212-242）とは無関係。`scale: proportional` なので島の厚みは配置時に
アンカーから決まり、参照列は「vanilla のどの範囲を島の上下に対応させるか」だけを
決める。既定の 64 / -64 では、vanilla Y が丸ごと 64 より上にある 5 本が
depthOf のクランプで幅ゼロに潰れる（実測）:

| ore | vanilla Y | 1チャンクあたりの供給 |
|---|---|---|
| ore_andesite_upper / granite_upper / diorite_upper | 64..128 | rarity 1/6 |
| ore_coal_upper | 136..319 | count 30（石炭全体の 6 割） |
| ore_iron_upper | 80..384 | count 90（鉄全体の 8 割） |

候補は 2 つ（`floor_y = -64` は動かさない＝2軸目になる）:

- **A: `surface_y: 128`** — 石3種と ore_iron_upper が幅を持つ。**ore_coal_upper は
  潰れたまま**（136 は 128 より上）。海面下の鉱石は下半分へ寄る（金 0.25..1.0 → 0.50..1.0）
- **B: `surface_y: 320`** — 5 本すべて解消。代わりに海面下が下位 1/4 に圧縮され、
  Y212-242 の島では金・ラピス・レッドストーンが Y212-219 の 8 ブロックに同居する

**分岐点**: 直す対象を issue #2 が挙げた石3種に限るか、供給の大半を占める
coal_upper / iron_upper まで含めるか。B は全部直すが、薄い島の鉱石分布を大きく変える。

### 付随して見えたこと（未裁定）

`ore_andesite_lower`（Y0..60・count 2）は既定値でも正しく Y54..77 に解決していて、
供給は `_upper`（rarity 1/6）の 12 倍ある。**issue #2 の「安山岩が生成されない」を
`_upper` の潰れだけでは説明しきれない。** 別の原因が残っている可能性がある。

### 検査の状況

- `tools/density_probe.py` は `main()` も `__main__` ブロックも持たず、実行しても
  何も出ない（docstring の "run the built-in report" は実体と合っていない）。
  島の帯の Y は `data/minecraft/worldgen/noise_settings/overworld.json` の
  `band_density` から直接読んだ（30-78 / 116-176 / 212-242）
- mod-063 側は `tools/check_ore_strategy.py` に幅ゼロ判定を足して機械照合済み。
  cosmos の 16 ore はどれも潰れていない

## 2026-08-08 一時停止時点（kura のゲームのためクライアント停止）

### 実機で確認済み・着地
- 緑空(#8FBA07) 解消 / 流体の柱 停止 / 雲 192→264 で島を貫通しない / 氷山除外
- 地形は Wave1 の乗算プロファイルに revert 済み（Wave1.5-A は kura 判定「めっちゃ劣化した」）

### 実装済み・**未実機確認**（再開時はここから）
最後のビルド `979df0e` を新規ワールドで見るところで停止した。見る点は3つ:
1. **アメジストジオードが消えたか** — vanilla は Y-58..30 に埋まって滅多に見ないだけで、
   HeightRangePlacement を持つため column_local が薄い島に投影して露出していた。除外で対応
2. **池の数** — 1/48 は kura「少なすぎるかも」→ **1/24** に。海が無い世界で水の唯一の入手源
3. **池の輪郭** — IsekaiAPI に `irregularity` を実装（v2.1.0 に畳んだ）。0.4 を適用。
   円盤の重ね置き（禿げた地面の原因）は撤去、単一 carve に戻した

### 残る既知課題
- **島の下面が板**（Wave1.5-A の revert で戻った唯一の未解決点）。1軸ずつ動かして毎回実機で見る
- 空の色が未確定（案A=vanilla のままが既定。B/C は同梱 datapack で比較可能）
- old_blended_noise の振幅がシード依存で、層の密度順序が6シード中1つで反転する（未裁定・11本に効く）

## 2026-09-04 issue #2（石バリアントが出ない）の決着

### 真因と解消

`ore_andesite_lower`（Y0..60・count 2）は既定値でも正しく Y54..77 に解決していて、供給は `_upper`（rarity 1/6）の 12 倍ある。issue #2 の残りの原因は**参照列が列の最上位の島しか見ていなかったこと**で、isekai-api `35f020b` で解消した（同一計測で下段 Y32..111 の andesite が 0→7,697、中段の「上に島あり/なし」の密度差が 36倍→1.07倍）。

先に入れた `5b6d5ff`（幅ゼロ帯を胴体へクランプ＋WARN）が効いたのは石炭（89%→98%）と鉄（35%→41%）で、石バリアントには効いていない。

計測器は `tools/probe_sky_ores.py`（RCON block-probe・`--expect-rock` の陽性対照つき）と `tools/analyze_sky_probe.py`。**バニラ基準の計測に mod-029 の runServer は使えない**（dev 専用で overworld を空にする上書きを持つので全部0を引く）。

### ジオードの記述が実体と食い違っていた

上の「アメジストジオードが消えたか — 除外で対応」は誤り。**実体は `exclusions` ではなく `rarity_filter` の 24→160 への上書き**。

**`35f020b` はこの調整の効き目を落とす。** `ore_strategy` は height_range を持つ全 feature を掃引するので、ジオードも列の島の数だけ出現機会が増える。kura が裁定した「頻度が多すぎる」への対応が、別の修正のついでに薄まる形になっている（[[feedback_approved_surface_freeze]] の型）。**公開前に修正前の露出へ戻す。**

### 未決のまま残すもの

- `sky.json` の参照列（`surface_y`/`floor_y`）。`35f020b` 後の全域で andesite がバニラ比 102%・granite 167% と過供給側に振れている。候補2つと分岐点は上の 2026-09-04 の節
- 深層岩を島に出す（kura 裁定 2026-09-04「出したほうが良いでしょ」）。機構は `isekai_api:strata` で API 拡張は不要。深さ N は未確定
- `WorldSurface.resolveYBelow` の終端走査コスト（`minBuildHeight` まで降りる分）。未測定
