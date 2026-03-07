import { aa as head } from './index2-BJkuhNcZ.js';
import { p as page } from './stores-LNmbpkhS.js';
import { t } from './i18n-DYMqjHva.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';
import './exports-BXvEiaiv.js';
import './state.svelte-BisSb15R.js';

function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    page.subscribe((p) => {
      p.params.id ?? "";
    });
    let segments = [];
    segments.map((s) => s.text).join(" ");
    segments.filter((s) => s.translation).map((s) => s.translation).join("");
    (() => {
      const result = [];
      let enBuf = "";
      let zhParts = [];
      let vocabBuf = [];
      let startTime = 0;
      let endTime = 0;
      for (const seg of segments) {
        if (!enBuf) startTime = seg.start;
        endTime = seg.end;
        enBuf += (enBuf ? " " : "") + seg.text;
        if (seg.translation) zhParts.push(seg.translation);
        vocabBuf = [...vocabBuf, ...seg.vocabulary ?? []];
        if (/[.!?]$/.test(seg.text.trim())) {
          result.push({
            en: enBuf.trim(),
            zh: zhParts.join(""),
            vocabulary: vocabBuf,
            start: startTime,
            end: endTime
          });
          enBuf = "";
          zhParts = [];
          vocabBuf = [];
        }
      }
      if (enBuf.trim()) {
        result.push({
          en: enBuf.trim(),
          zh: zhParts.join(""),
          vocabulary: vocabBuf,
          start: startTime,
          end: endTime
        });
      }
      return result;
    })();
    segments.flatMap((s) => s.vocabulary ?? []).filter((v, i, arr) => arr.findIndex((a) => a.word === v.word) === i);
    head("elvtci", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>${escape_html(t("loading"))} — ${escape_html(t("studyMode"))} — ReelScript</title>`);
      });
    });
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-elvtci">${escape_html(t("preparing"))}</div>`);
    }
    $$renderer2.push(`<!--]-->`);
  });
}

export { _page as default };
//# sourceMappingURL=_page.svelte-rM6B0JPq.js.map
