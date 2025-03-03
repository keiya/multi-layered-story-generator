多層的物語生成装置
Multi layered story generator

# Generators

## Plot Layer (1 出力)

ユーザーは LLM に大まかな物語の世界観、設定、価値観等を入力する。LLM はプロンプトと入力に従い、ワンレスポンス程度で収まるが、物語を要約できるほどの適度な長さのマスタープロット(登場人物、設定、価値観も含める)を生成する。

Input: 大まかな物語の世界観、設定、価値観等
Output: master_plot

## Backstory Layer

Plot Layer で生成したプロットをベースに世界観の設定を出力するレイヤー。

Input: master_plot
Output: backstories

## Character Layer

Plot Layer で生成したプロットをベースにキャラクターの設定を 1 レスポンスで出力するレイヤー。

Input: master_plot + backstories
Output: characters

## Chapter Layer (目安：5-20 出力、つまり 5-20 章)

Plot Layer で生成したプロットを章ごとに分割し、章ごとに 1 レスポンスを生成する。章を要約できるほどの適度な長さのプロットを生成する。入力はマスタープロットと前の章。出力はこの章のプロット(chapter_plot)と、物語を今後どう進めるか(chapter_intent)をメモした意図。
※1 章目には前の chapter_intent はないので chapter_intent[n-1]は渡さない。

Input: master_plot + backstories + characters + chapter_intent[n-1] + chapter_plot[n-1]
Output: chapter_plot[n] + chapter_intent[n]

## Timeline Layer (実装済み)

Chapter Layer で生成した各章をベースに各キャラクターのタイムラインを出力するレイヤー。
年月日とテキストが構造化された JSON を出力し、章ごとに追記していく。事実だけを書く。
なお、章の序列が日付順に沿っているとは限らない。

```json
[
  { // 1 章の出力
    "A": {
    "1995-02-12 03:00": "キャラクター A が生誕",
    "1995-05-15 05:00": "キャラクター A が魔法を習得"
    },
    "B": {
    "1993-01-22 02:00": "キャラクター B が生誕"
    }
  },
  { // 2 章の出力
    "A": {
    "1995-02-12 03:00": "キャラクター A が生誕",
    "1995-05-15 05:00": "キャラクター A が魔法を習得"
    "2003-05-15 05:00": "キャラクター A がキャラクター B と出会う"
    // ...
    "2016-11-03 12:00": "キャラクター A がボスに敗れて死亡"
    },
    "B": {
    "1993-01-22 02:00": "キャラクター B が生誕",
    "2003-05-15 05:00": "キャラクター B がキャラクター A と出会う"
    // ...
    }
  }
]
```

Input: master_plot + backstories + characters + chapter_plot[0:n] + all_characters_timeline[0:n-1]
Output: all_characters_timeline[0:n]

最後の章までイテレートすると、配列の数は章の数になっている。

## Section Layer (目安：3-5 出力、つまり 3-5 節) (実装済み)

Chapter Layer で生成したプロット(chapter_plot[n])をベースに、section_intent[m-1]と all_characters_timeline[n]も参考にしながら肉付けし、節ごとに 1 レスポンスを生成する。当該 Chapter 内の今までに生成した全 Section のプロットを渡す。
節を要約できるほどの適度な長さのプロットを生成する。
※1 節目には前の section_intent はないので section_intent[m-1]は渡さない。

Input: master_plot + backstories + characters + all_characters_timeline[n] + chapter_plot[n] + section_intent[m-1] + section_plot [0:m-1]
Output: section_plot[n] + section_intent[n]

※添字 m は Chapter に束縛されているものとする（つまり Chapter が変わったら 0 に戻る）

## Paragraph Layer (目安：2-15 出力、つまり 2-15 段落)

Section Layer で生成したプロット(section_plot[m])をベースに、paragraph_intent[i-1]を参考にしながら、前の段落(paragraph [i-1])と繋がるように、段落ごとに 1 レスポンスを生成する。
(繋がりをスムーズにするため 3 段落前から結合する)
この出力をつなげたものを物語の最終出力となる。
※最初らへんの段落には前の paragraph_intent はないので paragraph_intent[m-1]は渡さない。
※節が切り替わっても以前の節の段落は渡すが、章が切り替わったら段落は渡さない。

Input: master_plot + backstories + characters + all_characters_timeline[n] + section_plot[m] + paragraph [i-3:i-1] + paragraph_intent[i-1]
Output: paragraph[i] + paragraph_intent[i]

※添字 i は Chapter に束縛されているものとする（つまり Chapter が変わったら 0 に戻る）

# Filters

## Backstory Consistency Validation Filter (BCVF)

出力がプロット、世界観、キャラクター設定に沿っているかをチェックするフィルター。Chapter, Section 各層での plot, intent 出力に対して適用される。
何を直すべきかを出力する。

(chapter,section それぞれに適用する)
Input: master_plot + backstories + characters + plot[n] + intent[n]
Output: validation_output

## Chapter-Level Causal-Chain Validation Filter (Chapter-level CCVF)

出力が因果律に沿っているかをバリデーションするフィルター。全ての Chapter が出力された段階で、全ての Chapter 結合テキストに対して適用される。つまり、Chapter Layer までが終わった段階で 1 回実行される。
何を直すべきかを出力し、修正が必要な場合は全チャプタープロットを再生成する。

Input: master_plot + backstories + all_characters_timeline + characters + chapter_plot[]
Output: validation_output

## Section-Level Causal-Chain Validation Filter (Section-level CCVF)

出力が因果律に沿っているかをバリデーションするフィルター。現在の Chapter における 全 Section が出力された段階で全ての Section 結合テキストに対して適用される。つまり、Chapter の数だけ実行される。
何を直すべきかを出力し、修正が必要な場合は当該チャプターの全セクションプロットを再生成する。

Input: master_plot + backstories + all_characters_timeline + characters + chapter_plot[n] + section_plot[0:m]
Output: validation_output

## Style Filter

文体を修正するフィルター。Paragraph に対して適用される。
