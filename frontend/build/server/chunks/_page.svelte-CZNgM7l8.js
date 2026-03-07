import { aa as head, ac as ensure_array_like, ad as attr } from './index2-BJkuhNcZ.js';
import './exports-BXvEiaiv.js';
import './state.svelte-BisSb15R.js';
import { t } from './i18n-DYMqjHva.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';

function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let videos = [];
    let selectedIds = /* @__PURE__ */ new Set();
    let readyVideos = videos.filter((v) => v.status === "ready");
    let failedVideos = videos.filter((v) => v.status === "failed");
    videos.filter((v) => v.status !== "failed");
    let retryingIds = /* @__PURE__ */ new Set();
    let retryingAll = false;
    selectedIds.size;
    readyVideos.length > 0 && readyVideos.every((v) => selectedIds.has(v.id));
    head("1uha8ag", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>ReelScript</title>`);
      });
    });
    $$renderer2.push(`<section class="hero svelte-1uha8ag"><h1 class="svelte-1uha8ag">${escape_html(t("addVideo"))}</h1> <p class="svelte-1uha8ag">${escape_html(t("urlPlaceholder"))}</p> `);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<button class="btn btn-primary svelte-1uha8ag">${escape_html(t("loginToStart"))}</button>`);
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></section> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<section class="video-list svelte-1uha8ag"><h2 class="svelte-1uha8ag">${escape_html(t("myVideos"))}</h2> <div class="grid svelte-1uha8ag"><!--[-->`);
      const each_array = ensure_array_like(Array(3));
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        each_array[$$index];
        $$renderer2.push(`<div class="video-card card skeleton-card svelte-1uha8ag"><div class="skeleton-line short svelte-1uha8ag"></div> <div class="skeleton-line svelte-1uha8ag"></div> <div class="skeleton-line short svelte-1uha8ag"></div></div>`);
      }
      $$renderer2.push(`<!--]--></div></section>`);
    }
    $$renderer2.push(`<!--]--> `);
    if (failedVideos.length > 0) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<section class="failed-section svelte-1uha8ag"><div class="failed-header svelte-1uha8ag"><h2 class="svelte-1uha8ag">${escape_html(t("failedVideos2"))} (${escape_html(failedVideos.length)})</h2> <button class="btn btn-primary btn-sm svelte-1uha8ag"${attr("disabled", retryingAll, true)}>${escape_html(t("retryAll"))}</button></div> <div class="failed-list svelte-1uha8ag"><!--[-->`);
      const each_array_2 = ensure_array_like(failedVideos);
      for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
        let video = each_array_2[$$index_2];
        const isRetrying = retryingIds.has(video.id);
        $$renderer2.push(`<div class="failed-item card svelte-1uha8ag"><div class="failed-info svelte-1uha8ag"><div class="failed-top svelte-1uha8ag"><span class="badge badge-ig svelte-1uha8ag">${escape_html(video.source === "ig" ? "IG" : video.source === "youtube" ? "YT" : "?")}</span> <span class="failed-title svelte-1uha8ag">${escape_html(video.title || video.url)}</span></div> `);
        if (video.error_message) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<p class="failed-error svelte-1uha8ag">${escape_html(t("errorReason"))}: ${escape_html(video.error_message)}</p>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--></div> <div class="failed-actions svelte-1uha8ag"><button class="btn btn-primary btn-sm svelte-1uha8ag"${attr("disabled", isRetrying, true)}>${escape_html(isRetrying ? t("retrying") : t("retry"))}</button> <button class="btn btn-ghost btn-sm btn-danger-ghost svelte-1uha8ag">${escape_html(t("deleteFailed"))}</button></div></div>`);
      }
      $$renderer2.push(`<!--]--></div></section>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}

export { _page as default };
//# sourceMappingURL=_page.svelte-CZNgM7l8.js.map
