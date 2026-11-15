#import "../lib.typ": *

= Prompts and Model Responses <sec:app-prompts>

#show raw.where(block: true): set text(size: 7.5pt)

This appendix reproduces three recorded model requests and the answers to them. Every text below is copied byte for byte from the decision artifact that the orchestrator (M5) wrote for the request; nothing is re-rendered from code. Each artifact stores the system prompt, the user prompt and the SHA-256 digest of each. The digests given here were recomputed over the printed text and equal the stored ones. Long lines wrap at the margin; the line breaks of the original text are kept. The camera image that accompanies each user prompt is not reproduced; its place is marked "[annotated overhead image attached]". All three requests went to ER-2 (`gemini-robotics-er-2-preview`), with robots listed in ascending identifier order.

The system prompt is the same single line in all three requests (28 characters, SHA-256 `75357d685f238b6afd7738be9786fdafde641eb6ca9a3be7471939715a68a4de`):

```text
You are a helpful assistant.
```

== Prompt Version 3.4 in Intersection Run 1 <sec:app-prompt-v34>

The first request is the one excerpted in @fig:impl-prompt-excerpt: an analysis in episode 3 of intersection run 1 (coordination layer on), with the plan channel on#ev("4.39"). Its user prompt is 6,738 characters long, SHA-256 `cde5e27373b9c2b379b8b3395ba78097ca5bf1deb8adec9d92aef90ea29996a0`. The baseline of @sec:impl-vlm (5,804 characters, `6d08540f...`) is rendered by a test from a fixed two-robot test request, so its length and digest differ from those of a prompt recorded on a live scene#ev("4.17"). The image is sent after the text.

*User prompt.*

#raw(read("../assets/prompts/ib10-run1-e03-user.txt"), block: true, lang: "text")

```text
[annotated overhead image attached]
```

*Model answer* (raw text as returned, including the code fence the model added):

#raw(read("../assets/prompts/ib10-run1-e03-answer.txt"), block: true, lang: "text")

The answer is a `junction_clear` decision with a proposed plan. What the pipeline did with such decisions is reported in @sec:res-ib10-ab and is not repeated here.

== Second-Stage Retreat Selection Prompt <sec:app-prompt-stage2>

The second request is a second-stage (retreat-side) question (@sec:impl-vlm). After a validated `yield` naming `robot_1` as the yielder, the grounder (M3) kept two retreat candidates, and VLM reasoning (M2) asked the model to pick one of them by letter. The call comes from episode 9 of intersection run 1 (coordination layer on)#ev("4.40"). The user prompt is 1,092 characters long, SHA-256 `b8e68562e79aed8a42dcb82a063f1d548f718ba744b7067448a943092b8b36d1`. The image is the overhead frame with each candidate drawn as a lettered disc.

*User prompt.*

#raw(read("../assets/prompts/ib10-run1-e09-stage2-user.txt"), block: true, lang: "text")

```text
[annotated overhead image with lettered retreat positions attached]
```

*Model answer* (raw text):

#raw(read("../assets/prompts/ib10-run1-e09-stage2-answer.txt"), block: true, lang: "text")

Letters are assigned to the candidates afresh for each call and listed in a separately drawn order. In this call letter `B` stood for the grounder's candidate `A`, and candidate `A` was grounded#ev("4.40").

== Intersection Demonstration Take 5 <sec:app-prompt-take5>

The third request is the decision of intersection demonstration take 5 (request `df397030...`), traced in @fig:app-flow-take5 and simplified in @fig:ch6-flow-take5-simple#ev("6.81"). It uses the campaign's intersection prompt (@tab:ch5-prompts): the version 3.4 text with the plan channel on, plus two later additions that are not part of the pinned version: a block that lists, for each robot, the plan actions the verifier accepts in the current scene, and three sentences on how plan legs must be ordered. Because the prompt lists the accepted actions, the model's plan is a constrained selection from that list, not a free-form manoeuvre. The user prompt is 7,363 characters long, SHA-256 `cbc947c4e3285e682eddb463e6961a553544fbd3428376477f53a3c1407dbebc`. The image is sent after the text.

*User prompt.*

#raw(read("../assets/prompts/demo-ib-take5-user.txt"), block: true, lang: "text")

```text
[annotated overhead image attached]
```

*Model answer* (raw text):

#raw(read("../assets/prompts/demo-ib-take5-answer.txt"), block: true, lang: "text")

The plan passed the audit unchanged. Its only effect on execution was the back-out order, `robot_3` before `robot_4` instead of the default `robot_4` before `robot_3`, and that was a near-tie: 0.010 m apart in back-out cost, within the verifier's 0.15 m tolerance (@sec:res-demo-ib)#ev("6.39").
