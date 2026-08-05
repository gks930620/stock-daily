---
layout: default
title: 가상 포트폴리오 · 4인 비교
permalink: /portfolio/
---

{%- comment -%}
  벤치마크(bench)는 AI가 아니라 **기준선**이다 — 코스피를 사서 그냥 들고 있는 계좌.
  같은 화면에 두는 이유: 비교 대상이 없으면 "다 손해"인지 "시장보다 덜 잃었는지"를 말할 수 없다.
{%- endcomment -%}
{% assign ids = "stable,aggressive,normal1,normal2,bench" | split: "," %}
{%- comment -%} 평범형 2인은 동일 모델·동일 지시문의 대조군이라 같은 색 — 한 그룹임을 색으로 표시 {%- endcomment -%}
{% assign accents = "stable:#2f9e7f,aggressive:#d6452f,normal1:#5b7cb8,normal2:#5b7cb8,bench:#7a8899" | split: "," %}

{%- comment -%} 🏆 선두는 **AI 4인 중에서만** 뽑는다 (기준선과 겨루는 게 아니라 서로 겨루는 것) {%- endcomment -%}
{%- assign best = -99999 -%}
{%- assign ai_ids = "stable,aggressive,normal1,normal2" | split: "," -%}
{%- for id in ai_ids -%}{%- assign key = 'portfolio-' | append: id -%}{%- assign pf = site.data[key] -%}{%- if pf.return_pct > best -%}{%- assign best = pf.return_pct -%}{%- endif -%}{%- endfor -%}
{% assign bench = site.data['portfolio-bench'] %}

<div class="pfhub">
  {% include pf-switcher.html %}

  <header class="hh">
    <h1>같은 시장, 네 개의 뇌</h1>
    <p class="one">각자 1억 · 같은 데이터 · 손익으로 증명</p>
    <div class="brief">
      <span class="bi"><b>🛡️ 안정형</b> 지킨다 <i>opus</i></span>
      <span class="bi"><b>🚀 공격형</b> 밀어붙인다 <i>opus</i></span>
      <span class="bi"><b>🙂 평범형 1·2</b> 성향 없음 · 동일 지시문 대조군 <i>fable</i></span>
      <span class="bi bench"><b>📊 벤치마크</b> 코스피 매수 후 보유 · 판단 없음 <i>기준선</i></span>
    </div>
    {% if bench %}
    <p class="yard">📊 <b>기준선 {% if bench.return_pct >= 0 %}+{% endif %}{{ bench.return_pct }}%</b> — 아무 판단도 하지 않고 코스피만 들고 있었을 때의 성적입니다.
    이걸 못 이기면 <b>판단이 값을 못 한 것</b>입니다.</p>
    {% endif %}
  </header>

  <div class="grid">
    {% for id in ids %}
      {% assign key = 'portfolio-' | append: id %}
      {% assign pf = site.data[key] %}
      {% assign ac = "#666" %}
      {% for pair in accents %}{% assign kv = pair | split: ":" %}{% if kv[0] == id %}{% assign ac = kv[1] %}{% endif %}{% endfor %}
      <a class="pcard {% if id == 'bench' %}is-bench{% endif %}" href="{{ '/portfolio/' | append: id | append: '/' | relative_url }}" style="--ac:{{ ac }}">
        <div class="ptop">
          <span class="pemo">{{ pf.persona_emoji }}</span>
          <span class="pnm">{{ pf.persona_name }}</span>
          {% if id == 'bench' %}<span class="lead yard-tag">기준선</span>
          {% elsif best != 0 and pf.return_pct == best %}<span class="lead">🏆 선두</span>{% endif %}
        </div>
        {%- comment -%} 기준선 대비 초과수익 — 이 프로젝트에서 가장 중요한 한 줄 {%- endcomment -%}
        {% if id != 'bench' and bench %}
          {% assign exc = pf.return_pct | minus: bench.return_pct %}
          <div class="vsb {% if exc >= 0 %}u{% else %}d{% endif %}">기준선 대비 {% if exc >= 0 %}+{% endif %}{{ exc | round: 2 }}%p</div>
        {% endif %}
        <div class="ptag">{{ pf.persona_tag }}</div>
        <div class="ptot">{{ pf.total_value_str }}<small>원</small></div>
        <div class="pret {% if pf.return_pct >= 0 %}u{% else %}d{% endif %}">
          {% if pf.return_pct >= 0 %}▲ +{% else %}▼ {% endif %}{{ pf.return_pct }}%
          <span class="pday">오늘 {% if pf.day_chg_pct >= 0 %}+{% endif %}{{ pf.day_chg_pct }}%</span>
        </div>
        <div class="pmeta">
          <span>현금 <b>{{ pf.cash_weight_pct }}%</b></span>
          <span>보유 <b>{{ pf.holdings_view.size }}</b>종목</span>
          <span>{{ pf.days }}일차</span>
        </div>
        <div class="phold">
          {% if pf.holdings_view.size > 0 %}
            {% for h in pf.holdings_view limit:3 %}<span class="hp"><i style="background:{{ ac }}"></i>{{ h.name }} {{ h.weight_pct }}%</span>{% endfor %}
          {% else %}
            <span class="hp empty">아직 보유 없음 · 현금 100% (첫 매매 대기)</span>
          {% endif %}
        </div>
        <div class="pgo">자세히 보기 →</div>
      </a>
    {% endfor %}
  </div>

  <p class="foot">각 카드를 누르면 그 계좌의 <b>보유종목·평단·매매일지·자산곡선</b>이 증권앱처럼 열립니다.<br>
  ⚠️ <b>시작일이 다릅니다</b> — 🛡️안정·🚀공격은 2026-07-20 개시, 🙂평범형 1·2는 2026-07-28 개시. 누적 수익률을 나란히 볼 때 감안하세요(카드의 <b>N일차</b> 참고). · <a href="{{ '/' | relative_url }}">← 리포트</a></p>
</div>

<style>
.pfhub{--u:#d63c2f;--dn:#2563d0;}
.pfhub .hh h1{font-size:clamp(28px,5.4vw,42px);margin:.15em 0 .3em;letter-spacing:-.03em;line-height:1.15;}
.pfhub .hh .one{font-size:clamp(16px,2.2vw,19px);font-weight:700;color:var(--text);margin:0 0 14px;letter-spacing:-.01em;}
.pfhub .brief{display:flex;flex-wrap:wrap;gap:8px;}
.pfhub .bi{font-size:14.5px;color:var(--muted);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:7px 15px;white-space:nowrap;}
.pfhub .bi b{color:var(--text);font-weight:800;margin-right:5px;}
.pfhub .bi i{font-style:normal;font-size:11.5px;font-weight:700;color:var(--muted);border:1px solid var(--line);border-radius:5px;padding:1px 5px;margin-left:6px;vertical-align:1px;}
@media (max-width:520px){.pfhub .bi{white-space:normal;}}
.pfhub .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:22px 0 10px;}
.pfhub .pcard{display:block;text-decoration:none;color:var(--text);background:var(--card);border:1px solid var(--line);border-top:4px solid var(--ac);border-radius:15px;padding:18px 19px;box-shadow:var(--shadow);transition:transform .12s,box-shadow .12s;}
.pfhub .pcard:hover{transform:translateY(-3px);box-shadow:0 10px 26px rgba(0,0,0,.13);}
.pfhub .ptop{display:flex;align-items:center;gap:9px;}
.pfhub .pemo{font-size:22px;}
.pfhub .pnm{font-size:18px;font-weight:800;letter-spacing:-.01em;}
.pfhub .lead{margin-left:auto;font-size:12px;font-weight:800;color:var(--ac);background:color-mix(in srgb,var(--ac) 14%,transparent);padding:3px 9px;border-radius:999px;}
.pfhub .ptag{font-size:12.5px;color:var(--muted);margin:7px 0 14px;line-height:1.45;min-height:2.6em;}
.pfhub .ptot{font-size:26px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;}
.pfhub .ptot small{font-size:.5em;font-weight:600;color:var(--muted);margin-left:2px;}
.pfhub .pret{font-size:16px;font-weight:800;margin:2px 0 12px;font-variant-numeric:tabular-nums;}
.pfhub .pret.u{color:var(--u);} .pfhub .pret.d{color:var(--dn);}
.pfhub .pret .pday{font-size:12px;font-weight:600;color:var(--muted);margin-left:6px;}
.pfhub .pmeta{display:flex;gap:14px;font-size:12.5px;color:var(--muted);padding:10px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);}
.pfhub .pmeta b{color:var(--text);}
.pfhub .phold{display:flex;flex-wrap:wrap;gap:7px 12px;margin:12px 0;min-height:2.4em;}
.pfhub .hp{font-size:12.5px;color:var(--text);display:inline-flex;align-items:center;}
.pfhub .hp i{width:8px;height:8px;border-radius:3px;margin-right:5px;display:inline-block;}
.pfhub .hp.empty{color:var(--muted);}
.pfhub .pgo{font-size:13px;font-weight:700;color:var(--ac);}
.pfhub .foot{font-size:13px;color:var(--muted);margin-top:8px;}
/* 📊 벤치마크 — AI가 아니라 기준선이라 점선·회색으로 구분 */
.pfhub .bi.bench{border-style:dashed;}
.pfhub .yard{font-size:14px;color:var(--muted);margin:14px 0 0;padding:11px 14px;background:var(--card);border:1px dashed var(--line);border-radius:11px;}
.pfhub .yard b{color:var(--text);}
.pfhub .pcard.is-bench{border-style:dashed;border-top-style:solid;}
.pfhub .lead.yard-tag{background:color-mix(in srgb,var(--muted) 14%,transparent);color:var(--muted);}
.pfhub .vsb{font-size:12.5px;font-weight:800;margin:-8px 0 10px;font-variant-numeric:tabular-nums;}
.pfhub .vsb.u{color:var(--u);} .pfhub .vsb.d{color:var(--dn);}
</style>
