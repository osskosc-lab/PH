# PH v0.4 Phase 0A Pilot 結果報告

## 1. Executive Summary

**最終判定：`ACCESS_ASSUMPTION_FAIL`**  
**Pilot status：`PILOT_STOP`**

PH v0.3.3-r1で確定した、A0（Fast/Slow外部入力＋V/O観測）下のsingle shared-boundary node identityの構造的 `NON_IDENTIFIABLE` は凍結した。今回のPhase 0Aは、旧35/70D特徴量や分類器を変更せず、A1として選択的局所介入 `J_V` / `J_O` を追加した。

しかし、M0 positive control自身の双方向cross-effectが事前基準に達しなかった。

| 指標 | 結果 | 事前基準 |
|---|---:|---:|
| M0 `J_V -> O` | 0.019828 | >= 0.05 |
| M0 `J_O -> V` | 0.023578 | >= 0.05 |
| M0 `Gamma_cross` | 0.019828 | >= 0.05 |
| quality split 最小 target SNR | 0.218 | >= 2.0 |
| actuator calibration 最小 direct SNR | 7.640 | >= 5.0 |

したがって、今回の結果はPHの支持でも反証でもなく、**今回実装したA1 access modelが識別検査に必要な推定可能性を満たさなかった**ことを示す。

## 2. Gate Results

| Gate | 判定 |
|---|---|
| G0 Freshness / provenance | PASS |
| G1 Local selectivity calibration | PASS |
| G2 Excitation / SNR | **FAIL** |
| G3 M0 bidirectional cross-effect | **FAIL** |
| G4 Basic negative specificity | PASS |
| G5 Legacy mimic specificity | PASS |
| G6 Common-driver specificity | PASS |
| G7 M11-C separation | PASS（ただしA1成立前のため解釈不能） |
| G8 Profile / amplitude robustness | **FAIL** |
| G9 Capacity ladder | PASS |
| G10 Unrestricted oracle firewall | PASS |
| G11 Replay / numerical integrity | PASS |

## 3. Adversary and Oracle Audit

M11-Cは、`Z_V` / `Z_O`のduplicated stateに対し、事前固定された範囲でlocal leakage、shared innovation、cross-output couplingを許した。C0からC3までのcapacity ladderを評価し、C3が最も強い制約付き反例である。

| Capacity | fit objective | holdout Delta_ID |
|---|---:|---:|
| C0 separate / no cross | 0.105335 | 0.395555 |
| C1 measured local leakage | 0.092488 | 0.360037 |
| C2 plus shared innovation | 0.084772 | 0.336583 |
| C3 full constrained M11-C | 0.044199 | 0.217192 |

M11-CにはM0のhidden stateを与えていない。M11-UはM0のobservable traceをoracleとしてコピーし、holdout `Delta_ID = 0`となることを確認した。これは想定されたimpossibility canaryであり、global identifiabilityの根拠にはしない。

## 4. Claim Firewall

このPilotから言えるのは、指定した合成モデル族とA1実装において、M0 cross-effectの推定可能性Gateが成立しなかったということだけである。

言えないこと：

- PHが自然界に存在する／存在しない
- shared causal influenceやcommon causeが存在しない
- M11-C以外のalternative classが棄却された
- single latent nodeが人間、自己、意識、クオリア、魂である

## 5. Reproducibility

- Repository: `osskosc-lab/PH`
- PR: [#10](https://github.com/osskosc-lab/PH/pull/10)
- Branch commit: `87e45a2403c77d4daa6ae255f4235ea83be68711`
- GitHub Actions run: `33290949363`
- Workflow conclusion: `success`
- Artifact ID: `9725942518`
- Artifact ZIP SHA256: `7e065a0a7eec3b09ade9c779537642c8d2c522fbc9ffcef64309450234f70f4c`
- Config SHA256: `e28af7a433f2b22b30f9c660b9b0897c3bae05f77f5a1e0ea867f562887cf782`
- Preregistration SHA256: `53317d9c2bd5f884897e4a72ed329356cb0bf3b4c225be66ebef66d594491a5d`
- Full replay comparison: `PASS`
- Confirmatory data: **not generated**

## 6. Narrowest Defensible Continuation

本Phaseはここで停止する。次に許されるのは、結果を見て閾値・距離・M11-C制約を調整することではなく、`Phase 0A-r1`として、A1 accessの強度・観測SNR・局所介入波形を独立に再設計し、fresh namespaceで再較正することである。

M0の双方向cross-effectとquality Gateが再び成立しない限り、Confirmatoryへ進んではならない。成立した場合も、まずtarget label・介入位置・model identityをblind化したPhase 0Bを別途凍結する。
