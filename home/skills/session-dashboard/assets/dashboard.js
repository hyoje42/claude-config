/* Shared, dependency-free view model and browser application. */
(function () {
  "use strict";

  const FIELDS = [
    ["goal", "목표"], ["completed", "완료한 일"], ["current", "현재 작업"],
    ["remaining", "남은 일"], ["attention", "확인이 필요한 사항"], ["decisions", "주요 결정"]
  ];
  const STATUS_LABELS = { fresh: "최신 요약", stale: "이전 기록의 요약", invalid: "요약 근거 무효", missing: "요약 없음" };
  const KIND_LABELS = { user: "사용자 요청", assistant: "에이전트 응답", tool: "도구 결과", file: "파일 변경", compaction: "이전 대화 요약" };
  const LIVE_LABELS = { running: "실행 중", idle: "대기 중", waiting: "응답 대기", stopped: "실행 중지" };
  const list = (value) => Array.isArray(value) ? value : [];
  const string = (value) => typeof value === "string" ? value : "";
  const stamp = (value) => Date.parse(value) || 0;

  function summaryStatus(session) {
    if (!session.summary) return "missing";
    return ["fresh", "stale", "invalid"].includes(session.summary.status) ? session.summary.status : "invalid";
  }

  function claimsFor(session, field) {
    if (!["fresh", "stale"].includes(summaryStatus(session))) return [];
    return list(session.summary.fields && session.summary.fields[field]);
  }

  function previewFields(session) {
    const status = summaryStatus(session);
    if (!["fresh", "stale"].includes(status)) return [];
    const progress = claimsFor(session, "current").length || !claimsFor(session, "completed").length ?
      ["current", "현재 작업"] : ["completed", "기록된 진행"];
    return [["goal", "목표"], progress].map(([key, label]) => {
      const claims = claimsFor(session, key);
      return {
        key,
        label: status === "stale" ? "이전 요약 · " + label : label,
        known: claims.length > 0,
        text: claims.length ? string(claims[0].text) : "알 수 없음 · 확인 가능한 근거가 없습니다."
      };
    });
  }

  function needsAttention(session) {
    return summaryStatus(session) === "fresh" && claimsFor(session, "attention").length > 0;
  }

  function liveLabel(session) {
    return LIVE_LABELS[session.live && session.live.state] || "실행 상태 불명";
  }

  function hasWarning(session) {
    return list(session.warnings).length > 0 || Object.values(session.truncation || {}).some((value) => Number(value) > 0);
  }

  function resolveEvidence(session, refs) {
    // The collector's current events may reuse IDs after append or compaction.
    const captured = new Map(list(session.summary && session.summary.evidence).map((event) => [event.id, event]));
    return list(refs).map((ref) => captured.get(ref) || { id: ref, kind: "missing", timestamp: null, text: "보관된 근거를 찾을 수 없습니다." });
  }

  function selectSessions(sessions, query = "", filter = "all") {
    const needle = query.trim().toLocaleLowerCase();
    return list(sessions).filter((session) => {
      const status = summaryStatus(session);
      const matches = filter === "all" || filter === status ||
        (filter === "attention" && needsAttention(session)) ||
        (filter === "unknown" && liveLabel(session) === "실행 상태 불명") ||
        (filter === "warning" && hasWarning(session));
      if (!matches) return false;
      const search = [session.title, session.id, session.cwd,
        ...FIELDS.flatMap(([field]) => claimsFor(session, field).map((claim) => claim.text))].join("\n");
      return !needle || search.toLocaleLowerCase().includes(needle);
    }).sort((left, right) => Number(needsAttention(right)) - Number(needsAttention(left)) ||
      stamp(right.last_activity) - stamp(left.last_activity) || string(left.id).localeCompare(string(right.id)));
  }

  function counts(sessions) {
    return list(sessions).reduce((result, session) => {
      const status = summaryStatus(session);
      result.total += 1;
      result.attention += Number(needsAttention(session));
      result.outdated += Number(status === "stale" || status === "invalid");
      result.missing += Number(status === "missing");
      return result;
    }, { total: 0, attention: 0, outdated: 0, missing: 0 });
  }

  function pollDelay(seconds, failures = 0) {
    const base = Math.max(100, Math.min(3600000, Number(seconds) * 1000 || 5000));
    return failures ? Math.min(60000, base * (2 ** Math.min(failures, 3))) : base;
  }

  const model = { summaryStatus, claimsFor, previewFields, needsAttention, liveLabel, hasWarning, resolveEvidence, selectSessions, counts, pollDelay };
  if (typeof module !== "undefined" && module.exports) module.exports = model;
  if (typeof document === "undefined") return;

  const byId = (id) => document.getElementById(id);
  const nodes = new Map();
  const openDetails = new Map();
  let state = null;
  let offline = false;
  let busy = false;
  let failures = 0;
  let timer = null;
  let controller = null;
  let token = "";
  let pageActive = true;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function date(value) {
    if (!value || !Number.isFinite(Date.parse(value))) return "알 수 없음";
    return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date(value));
  }

  function details(session, key, label, className = "card-details") {
    const node = element("details", className);
    node.dataset.detailKey = key;
    node.open = openDetails.get(session.id + ":" + key) || false;
    node.addEventListener("toggle", () => openDetails.set(session.id + ":" + key, node.open));
    const heading = element("summary", "", label);
    heading.dataset.focusKey = key;
    node.append(heading);
    return node;
  }

  function eventNode(event) {
    const node = element("div", "event");
    node.append(element("p", "event-meta", (KIND_LABELS[event.kind] || "근거") + " · " + date(event.timestamp) + " · #" + string(event.id)),
      element("p", "event-text", event.kind === "missing" ? "이 요약에 보관된 근거를 찾을 수 없습니다. 요약 갱신이 필요합니다." : string(event.text)));
    return node;
  }

  function evidenceNode(session, claim, field, index) {
    const refs = list(claim.refs);
    const node = details(session, "evidence-" + field + "-" + index, "근거 보기 · " + refs.length + "개", "evidence");
    const body = element("div", "evidence-body");
    body.append(element("p", "detail-note", "요약 입력 당시 보관한 발췌입니다. 현재 기록과 다를 수 있습니다."));
    for (const event of resolveEvidence(session, refs)) body.append(eventNode(event));
    if (!refs.length) body.append(element("p", "unknown-field", "연결된 근거가 없습니다."));
    node.append(body);
    return node;
  }

  function summaryFields(session) {
    const node = details(session, "summary", "요약 상세 · 목표와 진행 상황");
    const body = element("div", "detail-body summary-fields");
    for (const [key, label] of FIELDS) {
      const section = element("section", "summary-field");
      section.append(element("h4", "", label));
      const claims = claimsFor(session, key);
      if (!claims.length) section.append(element("p", "unknown-field", "알 수 없음 · 요약에 확인 가능한 근거가 없습니다."));
      else {
        const items = element("ul");
        claims.forEach((claim, index) => {
          const item = element("li");
          item.append(element("p", "claim-text", string(claim.text)), evidenceNode(session, claim, key, index));
          items.append(item);
        });
        section.append(items);
      }
      body.append(section);
    }
    node.append(body);
    return node;
  }

  function identity(session) {
    const node = details(session, "identity", "세션 정보 · 전체 ID와 시각");
    const body = element("div", "detail-body");
    const data = element("dl", "identity-data");
    const live = session.live || {};
    const rows = [
      ["전체 세션 ID", session.id], ["프로젝트 경로", session.cwd || "알 수 없음"],
      ["실행 상태", liveLabel(session)],
      ["상태 출처", live.provenance === "transcript" ? "저장된 세션 기록" : live.provenance || "알 수 없음"],
      ["상태 관찰 시각", date(live.observed_at)], ["기록된 턴 상태", session.recorded_turn || "알 수 없음"],
      ["최근 기록", date(session.last_activity)], ["최근 수집", date(session.collected_at)],
      ["요약 작성", date(session.summary_at)], ["요약 입력 수집", date(session.summary && session.summary.input_at)]
    ];
    let identityText;
    for (const [label, value] of rows) {
      const term = element("dt", "", label);
      const definition = element("dd");
      if (label === "전체 세션 ID") {
        identityText = element("code", "", value);
        definition.append(identityText);
      } else definition.textContent = value;
      if (label === "최근 수집") definition.dataset.collectedAt = "true";
      data.append(term, definition);
    }
    const copy = element("button", "secondary copy-id", "세션 ID 복사");
    copy.type = "button";
    copy.dataset.focusKey = "copy-id";
    const feedback = element("p", "copy-result");
    feedback.setAttribute("role", "status");
    copy.addEventListener("click", async () => {
      try {
        if (!navigator.clipboard) throw new Error("unavailable");
        await navigator.clipboard.writeText(session.id);
        feedback.textContent = "세션 ID를 복사했습니다.";
      } catch (_) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(identityText);
        selection.removeAllRanges();
        selection.addRange(range);
        feedback.textContent = "세션 ID를 선택했습니다. 복사 단축키를 사용하세요.";
      }
    });
    body.append(data, copy, feedback, element("p", "detail-note", "최근 기록 시각이나 턴 종료만으로 현재 실행 여부 또는 전체 목표의 완료를 판단하지 않습니다. 시각은 브라우저의 현지 시간입니다."));
    if (session.summary) body.append(element("p", "detail-note", "요약 입력 ID: " + string(session.summary.snapshot_id)));
    node.append(body);
    return node;
  }

  function timeline(session) {
    const node = details(session, "timeline", "최근 기록 · " + list(session.events).length + "개");
    const body = element("div", "detail-body");
    body.append(element("p", "detail-note", "현재 수집된 기록입니다. 요약 근거는 요약 상세의 ‘근거 보기’에서 확인하세요."));
    const events = element("ol", "timeline");
    for (const event of list(session.events).slice().reverse()) {
      const item = element("li");
      item.append(eventNode(event));
      events.append(item);
    }
    if (!list(session.events).length) body.append(element("p", "unknown-field", "표시할 기록이 없습니다."));
    body.append(events);
    node.append(body);
    return node;
  }

  function warnings(session) {
    if (!hasWarning(session)) return null;
    const node = details(session, "warnings", "수집 주의 · 일부 기록이 생략되었을 수 있습니다", "card-warnings");
    const body = element("div", "detail-body");
    const items = element("ul");
    const labels = { recent_events: "최근 기록에서 생략한 항목", evidence_events: "요약 입력에서 생략한 항목", text_characters: "길이 제한으로 생략한 문자", excluded_events: "첨부·주입 내용 등 제외한 항목" };
    for (const message of list(session.warnings)) items.append(element("li", "", string(message)));
    for (const [key, label] of Object.entries(labels)) {
      const value = Number((session.truncation || {})[key]);
      if (value > 0) items.append(element("li", "", label + ": " + value.toLocaleString("ko-KR")));
    }
    body.append(items);
    node.append(body);
    return node;
  }

  function card(session) {
    const status = summaryStatus(session);
    const node = element("article", "session-card" + (needsAttention(session) ? " needs-attention" : ""));
    node.dataset.sessionId = session.id;
    node.dataset.summaryStatus = status;
    const heading = element("header", "card-heading");
    const badges = element("div", "card-badges");
    badges.append(element("span", "badge " + status, STATUS_LABELS[status]), element("span", "badge", liveLabel(session)));
    if (needsAttention(session)) badges.append(element("span", "badge attention", "확인 필요"));
    if (session.title_source === "automatic") badges.append(element("span", "badge", "자동 제목"));
    if (session.title_source === "id") badges.append(element("span", "badge", "제목 없음"));
    heading.append(badges, element("h3", "card-title", session.title || "제목 없음"),
      element("p", "card-project", session.cwd || "프로젝트를 알 수 없습니다."));
    const idLine = element("p", "identity-line");
    idLine.append(element("span", "", "세션"), element("code", "", string(session.id)));
    heading.append(idLine);
    const preview = element("div", "summary-preview");
    const messages = {
      missing: "아직 작성된 요약이 없습니다. 요약 갱신을 요청하면 근거를 바탕으로 목표와 진행 상황을 확인할 수 있습니다.",
      stale: "요약 이후 기록이 추가되었습니다. 아래 내용은 이전 기록을 바탕으로 하므로 최신 상황은 다시 확인해야 합니다.",
      invalid: "요약의 근거가 된 기록이 변경되어 내용을 표시하지 않습니다. 요약을 다시 작성해야 합니다."
    };
    if (messages[status]) preview.append(element("p", "summary-message " + status, messages[status]));
    if (status === "fresh" || status === "stale") {
      for (const field of previewFields(session)) {
        const section = element("div", "preview-field");
        section.append(element("span", "field-label", field.label));
        section.append(element("p", field.known ? "" : "unknown-field", field.text));
        preview.append(section);
      }
      if (needsAttention(session)) {
        const attention = element("div", "preview-field attention-preview");
        attention.append(element("span", "field-label", "확인 필요"), element("p", "", string(claimsFor(session, "attention")[0].text)));
        preview.append(attention);
      }
    }
    const times = element("div", "card-times");
    times.append(element("span", "", "최근 기록 " + date(session.last_activity)), element("span", "", "요약 작성 " + date(session.summary_at)));
    node.append(heading, preview, times);
    if (status === "fresh" || status === "stale") node.append(summaryFields(session));
    node.append(identity(session), timeline(session));
    const warning = warnings(session);
    if (warning) node.append(warning);
    return node;
  }

  function showEmpty(title, message) {
    byId("empty-state").hidden = false;
    byId("empty-title").textContent = title;
    byId("empty-message").textContent = message;
  }

  function renderSessions() {
    if (!state) return;
    const sessions = selectSessions(state.sessions, byId("search").value, byId("status-filter").value);
    const container = byId("sessions");
    const active = document.activeElement;
    const focusedCard = active && active.closest("[data-session-id]");
    const focusKey = active && active.dataset.focusKey;
    const focusId = focusedCard && focusedCard.dataset.sessionId;
    for (const session of sessions) {
      // Preserve focus and expanded details when only collection time changes.
      const signature = JSON.stringify([session.title, session.title_source, session.cwd, session.live,
        session.recorded_turn, session.last_activity, session.summary, session.summary_at,
        session.events, session.warnings, session.truncation]);
      const cached = nodes.get(session.id);
      if (!cached || cached.signature !== signature) {
        if (cached) for (const item of cached.node.querySelectorAll("details[data-detail-key]")) openDetails.set(session.id + ":" + item.dataset.detailKey, item.open);
        const replacement = card(session);
        if (cached && cached.node.isConnected) cached.node.replaceWith(replacement);
        nodes.set(session.id, { signature, node: replacement });
      }
      for (const time of nodes.get(session.id).node.querySelectorAll("[data-collected-at]")) time.textContent = date(session.collected_at);
    }
    const visible = new Set(sessions.map((session) => session.id));
    for (const node of Array.from(container.children)) if (!visible.has(node.dataset.sessionId)) node.remove();
    sessions.forEach((session, index) => {
      const node = nodes.get(session.id).node;
      if (container.children[index] !== node) container.insertBefore(node, container.children[index] || null);
    });
    const retained = new Set(state.sessions.map((session) => session.id));
    for (const id of nodes.keys()) if (!retained.has(id)) nodes.delete(id);
    if (focusId && focusKey && document.activeElement !== active) {
      const target = nodes.get(focusId);
      if (target && target.node.isConnected) {
        const item = Array.from(target.node.querySelectorAll("[data-focus-key]")).find((candidate) => candidate.dataset.focusKey === focusKey);
        const fallback = target.node.querySelector("summary");
        if (item || fallback) (item || fallback).focus({ preventScroll: true });
      }
    }
    byId("result-count").textContent = sessions.length + "개 표시 / 선택한 세션 " + state.sessions.length + "개";
    byId("empty-state").hidden = sessions.length > 0;
    if (!sessions.length) {
      if (!state.sessions.length) showEmpty("선택 범위에 세션이 없습니다", "프로젝트와 조회 기간을 확인하거나, 대화에서 표시할 세션을 지정해 주세요.");
      else showEmpty("검색 조건에 맞는 세션이 없습니다", "검색어를 지우거나 상태 필터를 ‘모든 세션’으로 바꿔 보세요.");
    }
    container.setAttribute("aria-busy", "false");
  }

  function render(view) {
    if (!view || view.schema !== 1 || !Array.isArray(view.sessions)) throw new Error("invalid-state");
    state = view;
    const selection = view.selection || {};
    const scope = list(selection.sessions).length ? "지정한 세션 " + selection.sessions.length + "개" : list(selection.projects).join(" · ") || "프로젝트를 알 수 없습니다";
    byId("context").textContent = (view.tool ? view.tool + " · " : "") + scope + (list(selection.sessions).length ? "" : " · 최근 " + selection.since_hours + "시간");
    const totals = counts(view.sessions);
    for (const [key, value] of Object.entries(totals)) byId("count-" + key).textContent = value;
    byId("collection-time").textContent = "최근 수집: " + date(view.collected_at) + " (현지 시간)";
    const messages = list(view.warnings);
    byId("global-warnings").hidden = messages.length === 0;
    byId("warnings-heading").textContent = "수집 안내 · " + messages.length + "개";
    byId("warning-list").replaceChildren(...messages.map((message) => element("li", "", string(message))));
    const omitted = Number(view.omitted_sessions) || 0;
    byId("omissions").hidden = !omitted;
    byId("omissions").textContent = "세션 수 제한으로 " + omitted + "개가 표시되지 않습니다. 더 넓은 범위가 필요하면 대화에서 표시 개수를 늘려 달라고 요청하세요.";
    renderSessions();
  }

  function connection(message, mode, error = false) {
    byId("connection-message").textContent = message;
    byId("connection-message").parentElement.classList.toggle("error", error);
    byId("mode").textContent = mode;
  }

  async function refresh() {
    if (offline || busy || !pageActive) return;
    clearTimeout(timer);
    if (!token) {
      connection("접속 정보가 없습니다. 대화에서 대시보드 시작을 요청하고 반환된 주소로 다시 열어 주세요.", "연결 필요", true);
      byId("refresh").disabled = true;
      byId("sessions").setAttribute("aria-busy", "false");
      byId("result-count").textContent = "연결되지 않음";
      showEmpty("대시보드에 연결할 수 없습니다", "접속 주소에 포함된 인증 정보가 필요합니다.");
      return;
    }
    busy = true;
    byId("refresh").disabled = true;
    controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    let retry = true;
    try {
      const response = await fetch("/api/state", { headers: { Authorization: "Bearer " + token }, signal: controller.signal,
        cache: "no-store", credentials: "omit", mode: "same-origin", redirect: "error", referrerPolicy: "no-referrer" });
      if (!response.ok) {
        retry = response.status !== 401 && response.status !== 403;
        throw new Error(retry ? "request-failed" : "authentication");
      }
      render(await response.json());
      failures = 0;
      connection("기록을 " + state.collect_seconds + "초 간격으로 확인합니다. 요약은 요청할 때만 갱신합니다.", "로컬 연결");
      byId("refresh").textContent = "기록 새로고침";
    } catch (error) {
      if (!pageActive) return;
      failures += 1;
      const message = !retry ? "접속 인증이 만료되었거나 허용되지 않았습니다. 대시보드를 다시 시작해 반환된 주소로 열어 주세요." :
        failures >= 3 ? "연속 3회 연결에 실패하여 자동 확인을 멈췄습니다. 서버 상태를 확인한 뒤 ‘다시 연결’을 눌러 주세요." :
          "기록을 가져오지 못했습니다. 잠시 후 다시 시도합니다 (" + failures + "/3).";
      connection(message + (state ? " 마지막으로 받은 내용을 표시하고 있습니다." : ""), "연결 끊김", true);
      byId("refresh").textContent = "다시 연결";
      if (!state) {
        showEmpty("기록을 불러오지 못했습니다", "연결을 복구하거나 에이전트에게 오프라인 HTML 내보내기를 요청하세요.");
        byId("result-count").textContent = "불러오기 실패";
      }
    } finally {
      clearTimeout(timeout);
      busy = false;
      controller = null;
      byId("refresh").disabled = false;
      byId("sessions").setAttribute("aria-busy", "false");
      if (pageActive && retry && failures < 3) timer = setTimeout(refresh, pollDelay(state && state.collect_seconds, failures));
    }
  }

  byId("search").addEventListener("input", renderSessions);
  byId("status-filter").addEventListener("change", renderSessions);
  document.querySelector(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    byId("sessions").focus();
    byId("sessions").scrollIntoView();
  });
  byId("refresh").addEventListener("click", () => { if (!busy) { failures = 0; refresh(); } });
  byId("summary-help").addEventListener("click", () => {
    const guide = byId("summary-guide");
    guide.hidden = !guide.hidden;
    byId("summary-help").setAttribute("aria-expanded", String(!guide.hidden));
  });
  window.addEventListener("pagehide", () => { pageActive = false; clearTimeout(timer); if (controller) controller.abort(); });
  window.addEventListener("pageshow", (event) => { if (event.persisted) { pageActive = true; refresh(); } });

  const embedded = byId("dashboard-data");
  if (embedded) {
    offline = true;
    byId("refresh").disabled = true;
    byId("refresh").textContent = "오프라인 사본";
    try {
      render(JSON.parse(embedded.textContent));
      connection("내보낸 시점의 사본입니다. 검색과 상세 보기는 인터넷 없이 사용할 수 있습니다.", "오프라인 사본");
    } catch (_) {
      connection("파일의 대시보드 데이터를 읽을 수 없습니다. 다시 내보내 주세요.", "파일 오류", true);
      byId("sessions").setAttribute("aria-busy", "false");
      byId("result-count").textContent = "파일 읽기 실패";
      showEmpty("오프라인 사본을 열지 못했습니다", "대화에서 대시보드 HTML을 다시 내보내 달라고 요청하세요.");
    }
  } else {
    const candidate = new URLSearchParams(window.location.hash.slice(1)).get("token") || "";
    token = /^[a-f0-9]{64}$/.test(candidate) ? candidate : "";
    // Retain the fragment so reload works; it is never sent in URLs or logs.
    refresh();
  }
})();
