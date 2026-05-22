const archiveStorageKey = "uma-archive-mode";
const userStorageKey = "uma-selected-user";

const homeState = {
    q: "",
    type: "",
    genre: "",
    year: "",
    tag: "",
    platform: "",
    sort: "recent",
    page: 1,
    limit: 12,
    decade: null,
};

document.addEventListener("DOMContentLoaded", () => {
    setupArchiveMode();

    const page = document.body.dataset.page;
    if (page === "home") {
        initHomePage();
    }
    if (page === "detail") {
        initDetailPage();
    }
});

function escapeHtml(value = "") {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

async function fetchJson(url, options = {}) {
    const config = {
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...(options.headers || {}),
        },
    };

    const response = await fetch(url, config);
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        throw new Error(data.detail || data || "Request failed.");
    }

    return data;
}

function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast) {
        return;
    }

    toast.textContent = message;
    toast.classList.add("visible");
    window.clearTimeout(showToast.timeoutId);
    showToast.timeoutId = window.setTimeout(() => {
        toast.classList.remove("visible");
    }, 2800);
}

function setupArchiveMode() {
    const toggle = document.getElementById("archive-toggle");
    const savedMode = window.localStorage.getItem(archiveStorageKey) === "true";
    document.body.classList.toggle("archive-mode", savedMode);
    if (toggle) {
        toggle.setAttribute("aria-pressed", String(savedMode));
        toggle.addEventListener("click", () => {
            const nextState = !document.body.classList.contains("archive-mode");
            document.body.classList.toggle("archive-mode", nextState);
            toggle.setAttribute("aria-pressed", String(nextState));
            window.localStorage.setItem(archiveStorageKey, String(nextState));
        });
    }
}

function formatMediaType(type) {
    return type ? type.charAt(0).toUpperCase() + type.slice(1) : "Media";
}

function getSelectedUserId() {
    return window.localStorage.getItem(userStorageKey) || "";
}

function setSelectedUserId(userId) {
    if (userId) {
        window.localStorage.setItem(userStorageKey, userId);
    } else {
        window.localStorage.removeItem(userStorageKey);
    }
}

function cardMarkup(item) {
    const genres = (item.genres || []).slice(0, 3).map((genre) => `<span class="tag">${escapeHtml(genre)}</span>`).join("");
    const summary = item.description || "No description available.";
    return `
        <a class="media-card" href="/items/${item.id}">
            <div class="media-thumb">
                <img src="${escapeHtml(item.thumbnail_url || "https://placehold.co/400x600/1f2a36/f0ead8?text=Archive")}" alt="${escapeHtml(item.title)} cover">
            </div>
            <span class="card-type">${escapeHtml(formatMediaType(item.type))}</span>
            <div>
                <h3>${escapeHtml(item.title)}</h3>
                <p class="card-meta">${escapeHtml(String(item.release_year || "Unknown year"))} | ${escapeHtml((item.creators || []).slice(0, 2).join(", ") || "Unknown creators")}</p>
            </div>
            <p class="card-meta">${escapeHtml(summary.slice(0, 110))}${summary.length > 110 ? "..." : ""}</p>
            <div class="tag-row">${genres}</div>
        </a>
    `;
}

function stackedMarkup(item) {
    return `
        <a class="stacked-item" href="/items/${item.id}">
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(formatMediaType(item.type))} | ${escapeHtml(String(item.release_year || ""))}</small>
            <span class="card-meta">${escapeHtml((item.genres || []).slice(0, 2).join(", ") || "No genres")}</span>
        </a>
    `;
}

function metricMarkup(metric) {
    return `
        <article class="metric-card">
            <span class="panel-kicker">${escapeHtml(metric.label)}</span>
            <strong>${escapeHtml(String(metric.value))}</strong>
            <small>${escapeHtml(metric.hint || "")}</small>
        </article>
    `;
}

function reviewFeedMarkup(review) {
    const mediaLabel = review.media_title ? `${review.media_title} (${formatMediaType(review.media_type)})` : "Archive note";
    return `
        <article class="review-feed-item">
            <strong>${escapeHtml(review.username || "Anonymous")}</strong>
            <span class="card-meta">${escapeHtml(mediaLabel)} | ${escapeHtml(String(review.rating))}/10</span>
            <p class="card-meta">${escapeHtml(review.comment || "")}</p>
        </article>
    `;
}

function breakdownMarkup(item) {
    return `
        <span class="breakdown-pill">
            <span>${escapeHtml(item.name)}</span>
            <strong>${escapeHtml(String(item.count))}</strong>
        </span>
    `;
}

function collectionMarkup(collection) {
    const previewItems = (collection.items || []).slice(0, 4);
    return `
        <article class="collection-card">
            <div>
                <span class="panel-kicker">${escapeHtml(collection.slug.replaceAll("-", " "))}</span>
                <h3>${escapeHtml(collection.title)}</h3>
            </div>
            <p>${escapeHtml(collection.description || "")}</p>
            <ul>
                ${previewItems.map((item) => `<li><a href="/items/${item.id}">${escapeHtml(item.title)}</a></li>`).join("")}
            </ul>
        </article>
    `;
}

function renderGrid(containerId, items, emptyMessage = "No archive entries found.") {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    if (!items || items.length === 0) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
        return;
    }

    container.innerHTML = items.map(cardMarkup).join("");
}

function renderStacked(containerId, items, emptyMessage = "Nothing to show yet.") {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    if (!items || items.length === 0) {
        container.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
        return;
    }

    container.innerHTML = items.map(stackedMarkup).join("");
}

function renderMetrics(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    container.innerHTML = (items || []).length
        ? items.map(metricMarkup).join("")
        : `<div class="empty-state">Metrics unavailable.</div>`;
}

function renderBreakdown(containerId, items, emptyMessage = "No breakdown available.") {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    container.innerHTML = (items || []).length
        ? items.map(breakdownMarkup).join("")
        : `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
}

function renderCollections(containerId, items, emptyMessage = "Collections will appear here.") {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    container.innerHTML = (items || []).length
        ? items.map(collectionMarkup).join("")
        : `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
}

function renderReviewFeed(containerId, items, emptyMessage = "No recent reviews yet.") {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    container.innerHTML = (items || []).length
        ? items.map(reviewFeedMarkup).join("")
        : `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
}

function updatePagination(total, page, limit, disabled = false) {
    const prevButton = document.getElementById("prev-page");
    const nextButton = document.getElementById("next-page");
    const label = document.getElementById("page-label");
    const totalPages = Math.max(1, Math.ceil(total / limit));

    if (label) {
        label.textContent = disabled ? "Static collection" : `Page ${page} of ${totalPages}`;
    }
    if (prevButton) {
        prevButton.disabled = disabled || page <= 1;
    }
    if (nextButton) {
        nextButton.disabled = disabled || page >= totalPages;
    }
}

async function initHomePage() {
    bindHomeEvents();

    try {
        const [facets, users] = await Promise.all([fetchJson("/catalog/facets"), fetchJson("/users")]);
        populateFilters(facets);
        populateUsers(users.items || [], "user-select");
        await Promise.all([loadDashboard(), loadCollections(), loadHighlights(), loadResults(), loadRecommendations()]);
    } catch (error) {
        renderMetrics("metrics-strip", []);
        renderCollections("collections-grid", [], error.message);
        renderGrid("trending-grid", [], error.message);
        renderGrid("recent-grid", [], error.message);
        renderGrid("results-grid", [], error.message);
        renderStacked("recommendations-grid", [], error.message);
        renderBreakdown("genre-breakdown", [], error.message);
        renderBreakdown("platform-breakdown", [], error.message);
        renderBreakdown("type-breakdown", [], error.message);
        renderReviewFeed("recent-reviews", [], error.message);
    }
}

function bindHomeEvents() {
    const searchForm = document.getElementById("search-form");
    const searchInput = document.getElementById("search-input");
    const typeFilter = document.getElementById("type-filter");
    const genreFilter = document.getElementById("genre-filter");
    const yearFilter = document.getElementById("year-filter");
    const tagFilter = document.getElementById("tag-filter");
    const platformFilter = document.getElementById("platform-filter");
    const sortFilter = document.getElementById("sort-filter");
    const userSelect = document.getElementById("user-select");
    const tabs = document.querySelectorAll(".tab-button");
    const prevButton = document.getElementById("prev-page");
    const nextButton = document.getElementById("next-page");

    searchForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        homeState.q = searchInput?.value.trim() || "";
        homeState.page = 1;
        homeState.decade = null;
        clearDecadeSelection();
        await loadResults();
    });

    typeFilter?.addEventListener("change", async (event) => {
        homeState.type = event.target.value;
        homeState.page = 1;
        syncTabs(homeState.type);
        await loadResults();
    });

    genreFilter?.addEventListener("change", async (event) => {
        homeState.genre = event.target.value;
        homeState.page = 1;
        await loadResults();
    });

    yearFilter?.addEventListener("change", async (event) => {
        homeState.year = event.target.value;
        homeState.page = 1;
        await loadResults();
    });

    tagFilter?.addEventListener("change", async (event) => {
        homeState.tag = event.target.value;
        homeState.page = 1;
        await loadResults();
    });

    platformFilter?.addEventListener("change", async (event) => {
        homeState.platform = event.target.value;
        homeState.page = 1;
        await loadResults();
    });

    sortFilter?.addEventListener("change", async (event) => {
        homeState.sort = event.target.value;
        homeState.page = 1;
        await loadResults();
    });

    userSelect?.addEventListener("change", async (event) => {
        setSelectedUserId(event.target.value);
        await loadRecommendations();
    });

    tabs.forEach((tab) => {
        tab.addEventListener("click", async () => {
            homeState.type = tab.dataset.type || "";
            homeState.page = 1;
            if (typeFilter) {
                typeFilter.value = homeState.type;
            }
            syncTabs(homeState.type);
            await loadResults();
        });
    });

    prevButton?.addEventListener("click", async () => {
        if (homeState.page > 1) {
            homeState.page -= 1;
            await loadResults();
        }
    });

    nextButton?.addEventListener("click", async () => {
        homeState.page += 1;
        await loadResults();
    });
}

function syncTabs(type) {
    document.querySelectorAll(".tab-button").forEach((tab) => {
        tab.classList.toggle("active", (tab.dataset.type || "") === type);
    });
}

function populateFilters(facets) {
    const typeFilter = document.getElementById("type-filter");
    const genreFilter = document.getElementById("genre-filter");
    const yearFilter = document.getElementById("year-filter");
    const tagFilter = document.getElementById("tag-filter");
    const platformFilter = document.getElementById("platform-filter");
    const decades = document.getElementById("decade-chips");

    if (typeFilter) {
        typeFilter.innerHTML = `<option value="">All types</option>${(facets.types || [])
            .map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(formatMediaType(type))}</option>`)
            .join("")}`;
    }
    if (genreFilter) {
        genreFilter.innerHTML = `<option value="">All genres</option>${(facets.genres || [])
            .map((genre) => `<option value="${escapeHtml(genre)}">${escapeHtml(genre)}</option>`)
            .join("")}`;
    }
    if (yearFilter) {
        yearFilter.innerHTML = `<option value="">All years</option>${(facets.years || [])
            .map((year) => `<option value="${escapeHtml(String(year))}">${escapeHtml(String(year))}</option>`)
            .join("")}`;
    }
    if (tagFilter) {
        tagFilter.innerHTML = `<option value="">All tags</option>${(facets.tags || [])
            .map((tag) => `<option value="${escapeHtml(tag)}">${escapeHtml(tag)}</option>`)
            .join("")}`;
    }
    if (platformFilter) {
        platformFilter.innerHTML = `<option value="">All platforms</option>${(facets.platforms || [])
            .map((platform) => `<option value="${escapeHtml(platform)}">${escapeHtml(platform)}</option>`)
            .join("")}`;
    }

    if (decades) {
        const chips = [`<button class="chip-button active" data-decade="">All eras</button>`]
            .concat(
                (facets.decades || []).slice(0, 8).map(
                    (decade) => `<button class="chip-button" data-decade="${escapeHtml(String(decade))}">${escapeHtml(String(decade))}s</button>`
                )
            )
            .join("");

        decades.innerHTML = chips;

        decades.querySelectorAll(".chip-button").forEach((button) => {
            button.addEventListener("click", async () => {
                const rawDecade = button.dataset.decade;
                homeState.decade = rawDecade ? Number(rawDecade) : null;
                homeState.page = 1;
                decades.querySelectorAll(".chip-button").forEach((chip) => chip.classList.remove("active"));
                button.classList.add("active");
                await loadResults();
            });
        });
    }

    const savedUser = getSelectedUserId();
    const userSelect = document.getElementById("user-select");
    if (userSelect && savedUser) {
        userSelect.value = savedUser;
    }
}

function clearDecadeSelection() {
    document.querySelectorAll("#decade-chips .chip-button").forEach((chip) => {
        chip.classList.toggle("active", chip.dataset.decade === "");
    });
}

function populateUsers(users, selectId) {
    const select = document.getElementById(selectId);
    if (!select) {
        return;
    }

    const blankLabel = selectId === "user-select" ? "Trending only" : "Select a user";
    select.innerHTML = `<option value="">${blankLabel}</option>${users
        .map((user) => `<option value="${escapeHtml(user.id)}">${escapeHtml(user.username)}</option>`)
        .join("")}`;

    const savedUser = getSelectedUserId();
    if (savedUser) {
        select.value = savedUser;
    }
}

async function loadDashboard() {
    const data = await fetchJson("/dashboard/summary");
    renderMetrics("metrics-strip", data.metrics);
    renderGrid("trending-grid", data.featured_media, "No featured archive entities found.");
    renderBreakdown("genre-breakdown", data.top_genres, "Genre coverage will appear here.");
    renderBreakdown("platform-breakdown", data.top_platforms, "Platform coverage will appear here.");
    renderBreakdown("type-breakdown", data.top_types, "Media mix will appear here.");
    renderReviewFeed("recent-reviews", data.recent_reviews, "Recent archive notes will appear here.");
}

async function loadCollections() {
    const data = await fetchJson("/collections?limit=4");
    renderCollections("collections-grid", data.items, "Collections will appear here.");
}

async function loadHighlights() {
    const recent = await fetchJson("/media?sort=recent&limit=6");
    renderGrid("recent-grid", recent.items, "No recent media found.");
}

async function loadRecommendations() {
    const userId = getSelectedUserId();
    const query = new URLSearchParams({ limit: "5" });
    if (userId) {
        query.set("user_id", userId);
    }
    const data = await fetchJson(`/recommendations?${query.toString()}`);
    renderStacked("recommendations-grid", data.items, "Recommendations will appear here.");
}

async function loadResults() {
    const title = document.getElementById("results-title");
    const meta = document.getElementById("results-meta");
    const params = new URLSearchParams();
    let endpoint = "/media";
    let paginationDisabled = false;

    if (homeState.type) {
        params.set("type", homeState.type);
    }
    if (homeState.genre) {
        params.set("genre", homeState.genre);
    }
    if (homeState.year) {
        params.set("year", homeState.year);
    }
    if (homeState.tag) {
        params.set("tag", homeState.tag);
    }
    if (homeState.platform) {
        params.set("platform", homeState.platform);
    }

    if (homeState.decade !== null) {
        endpoint = "/time-capsule";
        params.set("decade", String(homeState.decade));
        params.set("limit", "24");
        paginationDisabled = true;
        if (title) {
            title.textContent = `Time Capsule: ${homeState.decade}s`;
        }
    } else if (homeState.q) {
        endpoint = "/search";
        params.set("q", homeState.q);
        params.set("page", String(homeState.page));
        params.set("limit", String(homeState.limit));
        if (title) {
            title.textContent = `Search results for "${homeState.q}"`;
        }
    } else {
        params.set("page", String(homeState.page));
        params.set("limit", String(homeState.limit));
        params.set("sort", homeState.sort);
        if (title) {
            title.textContent = homeState.type ? `${formatMediaType(homeState.type)} archive` : "Browse the full catalog";
        }
    }

    try {
        const data = await fetchJson(`${endpoint}?${params.toString()}`);
        renderGrid("results-grid", data.items, "No matching media entities were found.");
        updatePagination(data.total || 0, data.page || 1, data.limit || homeState.limit, paginationDisabled);
        if (meta) {
            meta.textContent = `${data.total || 0} media entities available`;
        }
    } catch (error) {
        renderGrid("results-grid", [], error.message);
        updatePagination(0, 1, homeState.limit, true);
        if (meta) {
            meta.textContent = "";
        }
    }
}

async function initDetailPage() {
    const mediaId = document.body.dataset.mediaId;
    if (!mediaId) {
        return;
    }

    try {
        const users = await fetchJson("/users");
        populateUsers(users.items || [], "detail-user-select");
        bindDetailEvents(mediaId);
        await renderDetail(mediaId);
    } catch (error) {
        const detailHero = document.getElementById("detail-hero");
        if (detailHero) {
            detailHero.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
        }
    }
}

function bindDetailEvents(mediaId) {
    const userSelect = document.getElementById("detail-user-select");
    const watchlistButton = document.getElementById("watchlist-button");
    const historyButton = document.getElementById("history-button");
    const reviewForm = document.getElementById("review-form");
    const reviewRating = document.getElementById("review-rating");
    const reviewComment = document.getElementById("review-comment");

    userSelect?.addEventListener("change", (event) => {
        setSelectedUserId(event.target.value);
    });

    watchlistButton?.addEventListener("click", async () => {
        const userId = getSelectedUserId();
        if (!userId) {
            showToast("Select a user profile first.");
            return;
        }

        try {
            await fetchJson(`/users/${userId}/watchlist`, {
                method: "POST",
                body: JSON.stringify({ media_id: mediaId }),
            });
            showToast("Added to watchlist.");
        } catch (error) {
            showToast(error.message);
        }
    });

    historyButton?.addEventListener("click", async () => {
        const userId = getSelectedUserId();
        if (!userId) {
            showToast("Select a user profile first.");
            return;
        }

        try {
            await fetchJson(`/users/${userId}/history`, {
                method: "POST",
                body: JSON.stringify({ media_id: mediaId }),
            });
            showToast("Marked as accessed.");
        } catch (error) {
            showToast(error.message);
        }
    });

    reviewForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const userId = getSelectedUserId();
        if (!userId) {
            showToast("Select a user profile before reviewing.");
            return;
        }

        try {
            await fetchJson("/review", {
                method: "POST",
                body: JSON.stringify({
                    user_id: userId,
                    media_id: mediaId,
                    rating: Number(reviewRating.value),
                    comment: reviewComment.value.trim(),
                }),
            });
            reviewComment.value = "";
            showToast("Review added.");
            await renderDetail(mediaId);
        } catch (error) {
            showToast(error.message);
        }
    });
}

function detailMetaBox(label, value) {
    if (!value) {
        return "";
    }
    return `<div class="meta-box"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value)}</span></div>`;
}

function reviewMarkup(review) {
    return `
        <article class="review-card">
            <header>
                <strong>${escapeHtml(review.username || "Anonymous")}</strong>
                <span>${escapeHtml(String(review.rating))} / 10</span>
            </header>
            <p class="card-meta">${escapeHtml(review.comment || "")}</p>
        </article>
    `;
}

function renderAttributeList(data) {
    const container = document.getElementById("attribute-list");
    if (!container) {
        return;
    }

    const attributeEntries = [
        ["Creators", (data.creators || []).join(", ") || "Unknown creators"],
        ["Cast", (data.cast || []).join(", ") || "Not listed"],
        ["Genres", (data.genres || []).join(", ") || "Not listed"],
        ["Tags", (data.tags || []).join(", ") || "Not listed"],
        [
            "Archive analytics",
            `Views: ${data.analytics?.views || 0} | Watchlisted: ${data.analytics?.watchlisted || 0} | Search hits: ${data.analytics?.search_hits || 0}`,
        ],
    ];

    Object.entries(data.attributes || {}).forEach(([key, value]) => {
        attributeEntries.push([
            key.replaceAll("_", " "),
            Array.isArray(value) ? value.join(", ") : String(value),
        ]);
    });

    container.innerHTML = attributeEntries
        .map(
            ([label, value]) => `
                <div class="attribute-row">
                    <strong>${escapeHtml(label)}</strong>
                    <span>${escapeHtml(value)}</span>
                </div>
            `
        )
        .join("");
}

function renderGraph(graph) {
    const container = document.getElementById("graph-network");
    if (!container) {
        return;
    }

    if (!graph || !(graph.nodes || []).length) {
        container.innerHTML = `<div class="empty-state">No graph data is available for this entry.</div>`;
        return;
    }

    container.innerHTML = graph.nodes
        .map((node) => {
            const connectedEdges = (graph.edges || []).filter(
                (edge) => edge.source_id === node.id || edge.target_id === node.id
            );
            return `
                <article class="graph-node${node.id === graph.root_id ? " root" : ""}">
                    <header>
                        <strong>${escapeHtml(node.title)}</strong>
                        <span class="card-type">${escapeHtml(formatMediaType(node.type))}</span>
                    </header>
                    <span class="card-meta">${escapeHtml(String(node.release_year || "Unknown year"))}</span>
                    <ul>
                        ${connectedEdges
                            .map((edge) => {
                                const direction = edge.source_id === node.id ? "Links to" : "Linked from";
                                const otherNode = (graph.nodes || []).find(
                                    (candidate) => candidate.id === (edge.source_id === node.id ? edge.target_id : edge.source_id)
                                );
                                return `<li>${escapeHtml(direction)} ${escapeHtml(otherNode?.title || "unknown node")} via ${escapeHtml(edge.relation_type)}</li>`;
                            })
                            .join("")}
                    </ul>
                </article>
            `;
        })
        .join("");
}

async function renderDetail(mediaId) {
    const [data, graph] = await Promise.all([
        fetchJson(`/media/${mediaId}`),
        fetchJson(`/media/${mediaId}/graph`),
    ]);
    const detailHero = document.getElementById("detail-hero");
    const sourceList = document.getElementById("source-list");
    const reviewsList = document.getElementById("reviews-list");

    if (detailHero) {
        detailHero.innerHTML = `
            <div class="detail-poster">
                <img src="${escapeHtml(data.thumbnail_url || "https://placehold.co/400x600/1f2a36/f0ead8?text=Archive")}" alt="${escapeHtml(data.title)} cover">
            </div>
            <div class="detail-content">
                <span class="card-type">${escapeHtml(formatMediaType(data.type))}</span>
                <h1>${escapeHtml(data.title)}</h1>
                <p class="detail-meta">${escapeHtml(String(data.release_year || "Unknown year"))} | ${escapeHtml((data.creators || []).join(", ") || "Unknown creators")}</p>
                <p class="detail-summary">${escapeHtml(data.description || "No description available.")}</p>
                <div class="tag-row">
                    ${(data.genres || []).map((genre) => `<span class="tag">${escapeHtml(genre)}</span>`).join("")}
                    ${(data.tags || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
                </div>
                <div class="metadata-grid">
                    ${detailMetaBox("IMDb", data.ratings?.imdb ? `${data.ratings.imdb}` : "Not available")}
                    ${detailMetaBox("User rating", data.ratings?.user ? `${data.ratings.user}` : "Not rated")}
                    ${detailMetaBox("Cast", (data.cast || []).slice(0, 3).join(", "))}
                    ${detailMetaBox("Attributes", Object.entries(data.attributes || {}).slice(0, 2).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`).join(" | "))}
                </div>
            </div>
        `;
    }

    if (sourceList) {
        sourceList.innerHTML = (data.sources || []).length
            ? data.sources.map((source) => `
                <div class="source-item">
                    <div>
                        <strong>${escapeHtml(source.platform)}</strong>
                        <div class="card-meta">${escapeHtml(source.availability || "availability unknown")}</div>
                    </div>
                    <a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">Open source</a>
                </div>
            `).join("")
            : `<div class="empty-state">No external sources are currently attached to this entry.</div>`;
    }

    renderAttributeList(data);
    renderGraph(graph);
    renderGrid("related-grid", data.related_items || [], "No related media has been linked yet.");

    if (reviewsList) {
        reviewsList.innerHTML = (data.reviews || []).length
            ? data.reviews.map(reviewMarkup).join("")
            : `<div class="empty-state">No reviews yet. Add the first one.</div>`;
    }
}
