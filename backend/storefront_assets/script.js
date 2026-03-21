(function () {
  "use strict";

  const CONFIG = {
    sizeKeywords: ["tamanho", "tam", "size"],
    productCardSelectors: [
      ".js-product-container",
      ".js-item-product",
      ".item-product",
      ".product-item",
      ".js-product-item",
      ".js-item-container",
      "[data-product-id]",
      "[data-item-id]",
      ".product-card",
      ".js-product",
      "[data-product]",
      ".featured-product",
      ".showcase-item",
      ".product-showcase"
    ],
    productLinkSelectors: [
      "a[href*='/produto/']",
      "a[href*='/produtos/']",
      "a[href*='/product/']",
      "a[href*='/products/']",
      "a[href*='/p/']",
      "a.js-item-name",
      "a.item-name",
      "a.product-link",
      "a[href]"
    ],
    variantDataSelectors: [
      ".js-product-container[data-variants]",
      ".js-product-container[data-product-variants]",
      "[data-variants]",
      "[data-product-variants]"
    ],
    priceSelectors: [
      "#price_display .js-price-display",
      ".js-price-display",
      "#price_display",
      ".product-price .js-price-display",
      ".product-price",
      ".js-product-price",
      ".item-price",
      ".price-current",
      ".price",
      ".js-price",
      "[data-product-price]",
      "[data-price]"
    ],
    initialRetries: 12,
    retryDelayMs: 250,
    listDebounceMs: 260,
    maxBadgesPerCard: 3,
    initialListLoops: 2,
    initialListLoopDelayMs: 900,
    immediateListRunDelayMs: 90
  };

  const productDataCache = new Map();
  const listEnhancementState = { timer: null, observer: null };

  // Cache persistente em localStorage com TTL de 24h.
  // Evita re-fetch e re-parse de variantes a cada carregamento de página.
  const localCache = (function () {
    const PREFIX = "tn_apd_";
    const TTL = 86400000; // 24 horas em ms

    function get(key) {
      try {
        const raw = localStorage.getItem(PREFIX + key);
        if (!raw) return null;
        const entry = JSON.parse(raw);
        if (!entry || Date.now() - entry.t > TTL) {
          localStorage.removeItem(PREFIX + key);
          return null;
        }
        return entry.d;
      } catch (e) {
        return null;
      }
    }

    function set(key, data) {
      try {
        localStorage.setItem(PREFIX + key, JSON.stringify({ t: Date.now(), d: data }));
      } catch (e) {
        // localStorage cheio ou desabilitado — sem impacto funcional.
      }
    }

    return { get, set };
  })();
  const APP_SIGNATURE = "aparitrde-home-v2";
  window.__APARITRDE_BOOT__ = APP_SIGNATURE;
  if (window.console && typeof window.console.log === "function") {
    window.console.log("[aparitrde] boot", APP_SIGNATURE);
  }

  function isDebugEnabled() {
    return !!window.__APARITRDE_DEBUG__;
  }

  function debugLog(message, payload) {
    if (!isDebugEnabled() || !window.console || typeof window.console.log !== "function") return;
    if (typeof payload === "undefined") {
      window.console.log("[aparitrde]", message);
      return;
    }
    window.console.log("[aparitrde]", message, payload);
  }

  function normalizeText(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function parsePrice(value) {
    if (value == null || value === "") return null;

    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }

    const raw = String(value).trim();
    const cleaned = raw.replace(/[^\d,.\-]/g, "");

    if (!cleaned) return null;

    if (cleaned.includes(",") && cleaned.includes(".")) {
      const normalized = cleaned.replace(/\./g, "").replace(",", ".");
      const n = parseFloat(normalized);
      return Number.isFinite(n) ? n : null;
    }

    if (cleaned.includes(",")) {
      const n = parseFloat(cleaned.replace(",", "."));
      return Number.isFinite(n) ? n : null;
    }

    const n = parseFloat(cleaned);
    return Number.isFinite(n) ? n : null;
  }

  function formatBRL(value) {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL"
    }).format(value);
  }

  function getVariantsFromLS() {
    return window.LS && Array.isArray(window.LS.variants) ? window.LS.variants : [];
  }

  function getVariantPrice(variant) {
    if (!variant || typeof variant !== "object") return null;

    const centsFields = ["promotional_price_in_cents", "price_in_cents"];
    for (const field of centsFields) {
      const raw = variant[field];
      if (raw == null || raw === "") continue;
      const cents = parsePrice(raw);
      if (typeof cents === "number" && Number.isFinite(cents) && cents > 0) return cents / 100;
    }

    const numericFields = ["promotional_price_number", "price_number"];
    for (const field of numericFields) {
      const n = parsePrice(variant[field]);
      if (typeof n === "number" && Number.isFinite(n) && n > 0) return n;
    }

    const textFields = [
      "promotional_price_short",
      "promotional_price_with_currency",
      "promotional_price",
      "price_short",
      "price_with_currency",
      "price"
    ];
    for (const field of textFields) {
      const n = parsePrice(variant[field]);
      if (typeof n === "number" && Number.isFinite(n) && n > 0) return n;
    }

    return null;
  }

  function getDistinctVariantPrices(variants) {
    const prices = variants
      .map(v => getVariantPrice(v))
      .filter(v => typeof v === "number" && !Number.isNaN(v));

    return Array.from(new Set(prices)).sort((a, b) => a - b);
  }

  function isSizeKey(value) {
    const key = normalizeText(value);
    if (!key) return false;
    return CONFIG.sizeKeywords.some(keyword => key.includes(keyword));
  }

  function addRawSizeValue(raw, set) {
    if (raw == null) return;
    const text = String(raw).trim();
    if (!text) return;

    const normalized = normalizeText(text);
    if (!normalized || normalized === "selecione" || normalized === "escolha" || normalized === "tamanho") return;

    set.add(text);
  }

  function addSizeValueCollection(value, set) {
    if (value == null) return;

    if (Array.isArray(value)) {
      for (const item of value) addSizeValueCollection(item, set);
      return;
    }

    if (typeof value === "object") {
      if (Object.prototype.hasOwnProperty.call(value, "value")) addSizeValueCollection(value.value, set);
      if (Object.prototype.hasOwnProperty.call(value, "text")) addSizeValueCollection(value.text, set);
      if (Object.prototype.hasOwnProperty.call(value, "label")) addSizeValueCollection(value.label, set);
      return;
    }

    addRawSizeValue(value, set);
  }

  function collectSizeValuesFromVariant(variant, set) {
    if (!variant || typeof variant !== "object") return;

    for (let i = 1; i <= 3; i += 1) {
      const optionName =
        variant[`option_name_${i}`] ||
        variant[`option${i}_name`] ||
        variant[`variation_name_${i}`] ||
        variant[`attribute_name_${i}`];
      const optionValue =
        variant[`option${i}`] ||
        variant[`option_value_${i}`] ||
        variant[`variation_value_${i}`] ||
        variant[`attribute_value_${i}`];

      if (isSizeKey(optionName)) addRawSizeValue(optionValue, set);
    }

    const bags = [
      variant.values,
      variant.options,
      variant.attributes,
      variant.option_values,
      variant.variation_values
    ];

    for (const bag of bags) {
      if (!bag || typeof bag !== "object") continue;

      if (Array.isArray(bag)) {
        for (const item of bag) {
          if (!item || typeof item !== "object") continue;
          const name = item.name || item.label || item.option || item.key;
          if (isSizeKey(name)) {
            addSizeValueCollection(item.value != null ? item.value : item.text, set);
          }
        }
      } else {
        for (const [key, value] of Object.entries(bag)) {
          if (!isSizeKey(key)) continue;
          addSizeValueCollection(value, set);
        }
      }
    }
  }

  function sortSizeLabels(values) {
    const canonicalOrder = [
      "PP",
      "PPP",
      "P",
      "M",
      "G",
      "GG",
      "XG",
      "XGG",
      "EG",
      "U",
      "UNICO",
      "UNICA"
    ];
    const rank = new Map(canonicalOrder.map((v, idx) => [v, idx]));

    return values.slice().sort((a, b) => {
      const aKey = normalizeText(a).replace(/\s+/g, "").toUpperCase();
      const bKey = normalizeText(b).replace(/\s+/g, "").toUpperCase();

      const aRank = rank.has(aKey) ? rank.get(aKey) : 9999;
      const bRank = rank.has(bKey) ? rank.get(bKey) : 9999;
      if (aRank !== bRank) return aRank - bRank;

      const aNum = parseFloat(aKey.replace(",", "."));
      const bNum = parseFloat(bKey.replace(",", "."));
      const aIsNum = Number.isFinite(aNum);
      const bIsNum = Number.isFinite(bNum);

      if (aIsNum && bIsNum && aNum !== bNum) return aNum - bNum;
      return a.localeCompare(b, "pt-BR");
    });
  }

  function extractSizeValuesFromVariants(variants) {
    const set = new Set();

    for (const variant of variants) {
      collectSizeValuesFromVariant(variant, set);
    }

    // Fallback para o formato do Nuvemshop em cards de listagem:
    // data-variants embute option0/option1/option2 sem os nomes das opções,
    // então a detecção por nome nunca funciona. Quando nada foi coletado,
    // usa diretamente os valores de option0/1/2 de todas as variantes.
    if (!set.size) {
      for (const variant of variants) {
        for (let i = 0; i <= 2; i += 1) {
          addRawSizeValue(variant[`option${i}`], set);
        }
      }
    }

    return sortSizeLabels(Array.from(set));
  }

  function getProductDataFromVariants(variants) {
    if (!Array.isArray(variants) || variants.length < 2) return null;

    const prices = getDistinctVariantPrices(variants);
    if (!prices.length) return null;

    return {
      prices,
      minPrice: prices[0],
      hasDifferentPrices: prices.length >= 2,
      sizeValues: extractSizeValuesFromVariants(variants)
    };
  }

  function decodeHtmlEntities(text) {
    if (typeof text !== "string") return "";
    const textarea = document.createElement("textarea");
    textarea.innerHTML = text;
    return textarea.value;
  }

  function parseJsonString(value) {
    if (!value || typeof value !== "string") return null;

    const candidates = [];
    const pushCandidate = function (candidate) {
      if (!candidate || typeof candidate !== "string") return;
      if (!candidates.includes(candidate)) candidates.push(candidate);
    };

    pushCandidate(value.trim());
    pushCandidate(decodeHtmlEntities(value).trim());

    try {
      pushCandidate(decodeURIComponent(value).trim());
    } catch (e) {
      // Ignora encoding inválido.
    }

    for (const candidate of candidates) {
      try {
        return JSON.parse(candidate);
      } catch (e) {
        if (candidate.startsWith("'") && candidate.endsWith("'")) {
          try {
            return JSON.parse(candidate.slice(1, -1));
          } catch (e2) {
            // Continua tentando.
          }
        }
      }
    }

    return null;
  }

  function findVariantsInAnyObject(input, depth) {
    if (!input || depth > 5) return null;

    if (Array.isArray(input)) {
      if (input.length && input.every(item => item && typeof item === "object")) {
        const hasPriceLikeField = input.some(item =>
          ["price", "price_number", "price_in_cents", "promotional_price", "promotional_price_in_cents"].some(
            key => Object.prototype.hasOwnProperty.call(item, key)
          )
        );
        if (hasPriceLikeField) return input;
      }

      for (const item of input) {
        const found = findVariantsInAnyObject(item, depth + 1);
        if (found) return found;
      }
      return null;
    }

    if (typeof input === "object") {
      if (Array.isArray(input.variants)) return input.variants;

      for (const value of Object.values(input)) {
        const found = findVariantsInAnyObject(value, depth + 1);
        if (found) return found;
      }
    }

    return null;
  }

  function parseVariantsCandidate(value) {
    if (value == null || value === "") return null;

    if (Array.isArray(value)) {
      return value.length ? value : null;
    }

    if (typeof value === "object") {
      const fromObject = findVariantsInAnyObject(value, 0);
      return Array.isArray(fromObject) && fromObject.length ? fromObject : null;
    }

    if (typeof value === "string") {
      const parsed = parseJsonString(value);
      if (Array.isArray(parsed) && parsed.length) return parsed;

      const fromObject = findVariantsInAnyObject(parsed, 0);
      return Array.isArray(fromObject) && fromObject.length ? fromObject : null;
    }

    return null;
  }

  function extractBracketArray(text, startIndex) {
    let i = startIndex;
    let depth = 0;
    let inString = false;
    let quote = "";
    let escaping = false;

    for (; i < text.length; i += 1) {
      const ch = text[i];

      if (inString) {
        if (escaping) {
          escaping = false;
          continue;
        }
        if (ch === "\\") {
          escaping = true;
          continue;
        }
        if (ch === quote) {
          inString = false;
          quote = "";
        }
        continue;
      }

      if (ch === "'" || ch === "\"") {
        inString = true;
        quote = ch;
        continue;
      }

      if (ch === "[") depth += 1;
      if (ch === "]") {
        depth -= 1;
        if (depth === 0) return text.slice(startIndex, i + 1);
      }
    }

    return null;
  }

  function parseMaybeJsArray(arrayText) {
    if (!arrayText) return null;

    try {
      return JSON.parse(arrayText);
    } catch (e) {
      // eslint-disable-next-line no-new-func
      try {
        return Function(`"use strict"; return (${arrayText});`)();
      } catch (e2) {
        return null;
      }
    }
  }

  function extractVariantsFromScriptText(scriptText) {
    if (!scriptText) return null;

    // Padrões que incluem o colchete de abertura do array, evitando falsos
    // positivos em propriedades como "variants_count" ou "all_variants" que
    // podem aparecer antes de "variants" no JSON e capturar o array errado.
    const patterns = [
      /\bLS\.variants\s*=\s*\[/,
      /\bwindow\.LS\.variants\s*=\s*\[/,
      /"variants"\s*:\s*\[/,
      /'variants'\s*:\s*\[/,
      /\bvariants\s*:\s*\[/,
      /\bvariants\s*=\s*\[/
    ];

    for (const pattern of patterns) {
      const match = pattern.exec(scriptText);
      if (!match) continue;

      // O colchete de abertura é o último caractere do match.
      const bracketStart = match.index + match[0].length - 1;
      const arrayText = extractBracketArray(scriptText, bracketStart);
      const parsed = parseMaybeJsArray(arrayText);
      if (Array.isArray(parsed) && parsed.length) return parsed;
    }

    return null;
  }

  function extractSizeValuesFromProductDOM(doc) {
    const set = new Set();

    const selectNodes = doc.querySelectorAll(
      "select[name*='tamanho'], select[name*='size'], select[id*='tamanho'], select[id*='size'], select[data-option-name*='tamanho'], select[data-option-name*='size']"
    );
    for (const select of selectNodes) {
      const options = select.querySelectorAll("option");
      for (const option of options) {
        const value = option.value || option.textContent;
        addRawSizeValue(value, set);
      }
    }

    const inputNodes = doc.querySelectorAll(
      "input[name*='tamanho'], input[name*='size'], input[data-option-name*='tamanho'], input[data-option-name*='size']"
    );
    for (const input of inputNodes) {
      const label = input.id ? doc.querySelector(`label[for='${input.id}']`) : null;
      const value = (label && label.textContent) || input.value;
      addRawSizeValue(value, set);
    }

    return sortSizeLabels(Array.from(set));
  }

  function extractProductDataFromHtml(html) {
    if (!html || typeof html !== "string") return null;

    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");

    let variants = null;

    const dataNodes = doc.querySelectorAll(CONFIG.variantDataSelectors.join(","));
    for (const node of dataNodes) {
      const direct = [
        node.getAttribute("data-variants"),
        node.getAttribute("data-product-variants")
      ];

      for (const candidate of direct) {
        const parsed = parseVariantsCandidate(candidate);
        if (parsed) {
          variants = parsed;
          break;
        }
      }
      if (variants) break;
    }

    if (!variants) {
      const scripts = doc.querySelectorAll("script");
      for (const script of scripts) {
        const type = (script.getAttribute("type") || "").toLowerCase();
        const text = script.textContent || "";
        if (!text) continue;

        if (type.includes("json")) {
          const parsedJson = parseVariantsCandidate(text);
          if (Array.isArray(parsedJson) && parsedJson.length) {
            variants = parsedJson;
            break;
          }
        }

        const fromScript = extractVariantsFromScriptText(text);
        if (Array.isArray(fromScript) && fromScript.length) {
          variants = fromScript;
          break;
        }
      }
    }

    const data = getProductDataFromVariants(variants || []);
    if (!data) return null;

    if (!data.sizeValues.length) {
      data.sizeValues = extractSizeValuesFromProductDOM(doc);
    }

    return data;
  }

  async function fetchProductData(url) {
    if (!url) return null;

    // localStorage primeiro — evita re-fetch entre carregamentos de página.
    const lsCached = localCache.get(url);
    if (lsCached) return lsCached;

    if (productDataCache.has(url)) return productDataCache.get(url);

    const promise = (async function () {
      try {
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok) return null;
        const html = await response.text();
        const data = extractProductDataFromHtml(html);
        if (data) localCache.set(url, data);
        return data;
      } catch (e) {
        return null;
      }
    })();

    productDataCache.set(url, promise);
    return promise;
  }

  function isVisible(el) {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
    if (el.offsetWidth === 0 && el.offsetHeight === 0) return false;
    return true;
  }

  function findPriceNode(root) {
    const scope = root && root.querySelector ? root : document;

    for (const selector of CONFIG.priceSelectors) {
      const nodes = scope.querySelectorAll(selector);
      for (const node of nodes) {
        if (!isVisible(node)) continue;

        const classText = `${node.className || ""} ${node.id || ""}`.toLowerCase();
        if (classText.includes("compare") || classText.includes("old") || classText.includes("list")) continue;

        return node;
      }
    }

    return null;
  }

  function setTextPrice(node, text) {
    if (!node) return;
    node.textContent = text;
  }

  function isProductPage() {
    return !!(window.LS && window.LS.product && Array.isArray(window.LS.variants));
  }

  function qualifiesForStartingFromCurrentProduct() {
    const variants = getVariantsFromLS();
    if (!variants.length || variants.length < 2) return null;

    const prices = getDistinctVariantPrices(variants);
    if (prices.length < 2) return null;

    return { minPrice: prices[0] };
  }

  function applyStartingFromOnProductPage(root) {
    const info = qualifiesForStartingFromCurrentProduct();
    if (!info) return false;

    const priceNode = findPriceNode(root);
    if (!priceNode) return false;

    setTextPrice(priceNode, `A partir de: ${formatBRL(info.minPrice)}`);
    priceNode.setAttribute("data-starting-from-applied", "true");
    return true;
  }

  function applyExactVariantPrice(variant) {
    if (!variant) return false;

    const price = getVariantPrice(variant);
    if (price == null) return false;

    let root = document;
    if (variant.element) {
      const scopedRoot = document.querySelector(variant.element);
      if (scopedRoot) root = scopedRoot;
    }

    const priceNode = findPriceNode(root) || findPriceNode(document);
    if (!priceNode) return false;

    setTextPrice(priceNode, formatBRL(price));
    priceNode.setAttribute("data-starting-from-applied", "false");
    return true;
  }

  function bootInitialProductState() {
    let tries = 0;

    const tick = function () {
      tries += 1;
      const done = applyStartingFromOnProductPage(document);

      if (!done && tries < CONFIG.initialRetries) {
        window.setTimeout(tick, CONFIG.retryDelayMs);
      }
    };

    tick();
  }

  function bootProductVariantListener() {
    if (!window.LS || typeof window.LS.registerOnChangeVariant !== "function") return;

    window.LS.registerOnChangeVariant(function (variant) {
      window.setTimeout(function () {
        applyExactVariantPrice(variant);
      }, 30);

      window.setTimeout(function () {
        applyExactVariantPrice(variant);
      }, 220);
    });
  }

  function getCardLink(card) {
    if (!card || !card.querySelector) return null;

    const storedUrl = card.getAttribute("data-tn-product-url");
    if (storedUrl) return storedUrl;

    const directAttrs = ["data-url", "data-product-url", "data-item-url", "data-href"];
    for (const attr of directAttrs) {
      const raw = card.getAttribute(attr);
      const normalized = normalizeProductUrl(raw);
      if (normalized) {
        card.setAttribute("data-tn-product-url", normalized);
        return normalized;
      }
    }

    for (const selector of CONFIG.productLinkSelectors) {
      const link = card.querySelector(selector);
      if (!link || !link.getAttribute) continue;
      const normalized = normalizeProductUrl(link.getAttribute("href"));
      if (!normalized) continue;
      card.setAttribute("data-tn-product-url", normalized);
      return normalized;
    }

    return null;
  }

  function hasVariantDataInNode(node) {
    if (!node) return false;
    if (node.matches && node.matches(CONFIG.variantDataSelectors.join(","))) return true;
    if (!node.querySelector) return false;
    return !!node.querySelector(CONFIG.variantDataSelectors.join(","));
  }

  function isLikelyCardContainer(node) {
    if (!node || node.nodeType !== 1) return false;
    if (node.matches && node.matches(CONFIG.productCardSelectors.join(","))) return true;
    if (hasVariantDataInNode(node)) return true;
    return !!findPriceNode(node);
  }

  function getCardContainerFromLink(link) {
    if (!link || !link.closest) return null;

    const strictContainer = link.closest(
      ".js-product-container, .js-item-product, .item-product, .product-item, .js-product-item, .js-item-container, [data-product-id], [data-item-id]"
    );
    if (strictContainer) return strictContainer;

    const genericContainer = link.closest("article, li, div");
    if (!genericContainer) return link.parentElement || null;

    if (isLikelyCardContainer(genericContainer)) return genericContainer;
    const parentContainer = genericContainer.parentElement;
    if (isLikelyCardContainer(parentContainer)) return parentContainer;

    return genericContainer;
  }

  function isSkippableHref(rawHref) {
    if (!rawHref || typeof rawHref !== "string") return true;

    const href = rawHref.trim();
    if (!href) return true;
    if (href.startsWith("#")) return true;
    if (/^(mailto:|tel:|javascript:)/i.test(href)) return true;
    return false;
  }

  function normalizeProductUrl(rawHref) {
    if (isSkippableHref(rawHref)) return null;

    try {
      const url = new URL(rawHref, window.location.origin);
      if (url.origin !== window.location.origin) return null;
      if (!url.pathname || url.pathname === "/") return null;
      if (/\.(png|jpg|jpeg|gif|svg|webp|pdf|mp4|webm|css|js)$/i.test(url.pathname)) return null;
      url.hash = "";
      url.search = "";
      return url.toString();
    } catch (e) {
      return null;
    }
  }

  function getCardsWithProductLinks() {
    const set = new Set();
    const variantNodesCount = { total: 0 };

    for (const selector of CONFIG.productCardSelectors) {
      const cards = document.querySelectorAll(selector);
      for (const card of cards) {
        if (!getCardLink(card)) continue;
        set.add(card);
      }
    }

    // Foco em variações embutidas no card (layout base / temas derivados).
    const variantNodes = document.querySelectorAll(CONFIG.variantDataSelectors.join(","));
    variantNodesCount.total = variantNodes.length;
    for (const node of variantNodes) {
      const card = getCardContainerFromLink(node.closest("a[href]") || node);
      if (!card) continue;
      if (!isLikelyCardContainer(card)) continue;

      if (!getCardLink(card)) {
        const firstLink = card.querySelector("a[href]");
        const normalized = firstLink ? normalizeProductUrl(firstLink.getAttribute("href")) : null;
        if (normalized) card.setAttribute("data-tn-product-url", normalized);
      }

      if (!getCardLink(card)) continue;
      set.add(card);
    }

    // Fallback por links dentro de containers prováveis de produto.
    const scopedLinks = document.querySelectorAll(
      ".js-product-container a[href], .js-item-product a[href], .item-product a[href], .product-item a[href], .js-product-item a[href], [data-product-id] a[href], [data-item-id] a[href]"
    );
    for (const link of scopedLinks) {
      const url = normalizeProductUrl(link.getAttribute("href"));
      if (!url) continue;

      const card = getCardContainerFromLink(link);
      if (!card) continue;
      if (!isLikelyCardContainer(card)) continue;

      card.setAttribute("data-tn-product-url", url);
      set.add(card);
    }

    // Fallback final: se nenhum card foi encontrado pelos seletores padrão,
    // varre qualquer link de produto que tenha um nó de preço visível no container pai.
    // Útil para home pages e seções de destaque com markup não padrão.
    if (!set.size) {
      const genericLinks = document.querySelectorAll(
        'a[href*="/produto/"], a[href*="/produtos/"], a[href*="/products/"], a[href*="/product/"], a[href*="/p/"]'
      );
      for (const link of genericLinks) {
        const url = normalizeProductUrl(link.getAttribute("href"));
        if (!url) continue;
        const card = getCardContainerFromLink(link);
        if (!card) continue;
        if (!findPriceNode(card)) continue;
        card.setAttribute("data-tn-product-url", url);
        set.add(card);
      }
    }

    debugLog("cards encontrados", {
      total: set.size,
      variantNodes: variantNodesCount.total
    });

    // Exclui o container de detalhe do produto (página de produto individual).
    // Sem isso, o MutationObserver re-processa o produto e sobrescreve o preço
    // da variação selecionada com o preço mínimo ("A partir de:").
    return Array.from(set).filter(function (card) {
      return !card.classList.contains("js-product-detail") &&
             !card.closest(".js-product-detail") &&
             card.id !== "single-product";
    });
  }

  function findVariantsFromCardData(card) {
    if (!card || !card.querySelectorAll) return null;

    const nodes = [card].concat(Array.from(card.querySelectorAll(CONFIG.variantDataSelectors.join(","))));

    for (const node of nodes) {
      const directCandidates = [
        node.getAttribute && node.getAttribute("data-variants"),
        node.getAttribute && node.getAttribute("data-product-variants")
      ];

      for (const candidate of directCandidates) {
        const parsed = parseVariantsCandidate(candidate);
        if (parsed) return parsed;
      }

      if (!node.attributes) continue;
      for (const attr of Array.from(node.attributes)) {
        const attrName = normalizeText(attr.name);
        if (!attrName.includes("variant")) continue;
        const parsed = parseVariantsCandidate(attr.value);
        if (parsed) return parsed;
      }
    }

    const scriptNodes = card.querySelectorAll("script[type*='json']");
    for (const scriptNode of scriptNodes) {
      const parsed = parseVariantsCandidate(scriptNode.textContent || "");
      if (parsed) return parsed;
    }

    return null;
  }

  function getThemeColor(varNames, fallback) {
    const root = window.getComputedStyle(document.documentElement);
    for (const name of varNames) {
      const value = (root.getPropertyValue(name) || "").trim();
      if (value) return value;
    }
    return fallback;
  }

  function getBadgeColors() {
    const primary = getThemeColor(
      ["--primary-color", "--color-primary", "--primary", "--main-color", "--main-primary-color"],
      null
    );
    if (primary) return { primary, background: "#ffffff" };

    // Fallback: lê a cor real do botão primário do tema (Toluca não expõe CSS variables).
    const btn = document.querySelector(".btn-primary, .add-to-cart, .js-add-to-cart, [data-action='add-to-cart']");
    if (btn) {
      const bg = window.getComputedStyle(btn).backgroundColor;
      if (bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") {
        return { primary: bg, background: "#ffffff" };
      }
    }

    return { primary: "#111111", background: "#ffffff" };
  }

  function applyStartingFromOnCard(card, minPrice) {
    const priceNode = findPriceNode(card);
    if (!priceNode) return;

    // Já aplicado E prefixo ainda presente — nada a fazer.
    // Se o Nuvemshop re-renderizar o nó de preço (data-store="product-item-price-*"),
    // o span .tn-from-prefix some mas data-tn-from-applied fica no atributo do nó
    // sobrevivente. Verificar os dois garante reaplicação nesse caso.
    if (priceNode.getAttribute("data-tn-from-applied") === "true" &&
        priceNode.querySelector(".tn-from-prefix")) return;

    priceNode.textContent = "";
    const prefixEl = document.createElement("span");
    prefixEl.className = "tn-from-prefix";
    prefixEl.textContent = "A partir de: ";
    prefixEl.style.cssText = "font-weight:700;";
    priceNode.appendChild(prefixEl);
    priceNode.appendChild(document.createTextNode(formatBRL(minPrice)));
    priceNode.setAttribute("data-tn-from-applied", "true");
  }

  function upsertSizeBadges(card, sizeValues) {
    const shouldShow = Array.isArray(sizeValues) && sizeValues.length >= 2;
    const existing = card.querySelector(".tn-size-badges");

    if (!shouldShow) {
      if (existing) existing.remove();
      return;
    }

    const style = window.getComputedStyle(card);
    if (style.position === "static") {
      card.style.position = "relative";
    }

    const wrap = existing || document.createElement("div");
    wrap.className = "tn-size-badges";
    wrap.setAttribute(
      "style",
      "position:absolute;top:8px;right:8px;display:flex;flex-direction:column;align-items:flex-end;gap:4px;z-index:4;pointer-events:none;"
    );

    wrap.textContent = "";

    const colors = getBadgeColors();
    const values = sizeValues.slice(0, CONFIG.maxBadgesPerCard);

    for (const value of values) {
      const badge = document.createElement("span");
      badge.textContent = value;
      badge.setAttribute(
        "style",
        `display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;border-radius:4px;font-size:11px;font-weight:700;line-height:1.2;background:${colors.primary};color:${colors.background};max-width:72px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;`
      );
      wrap.appendChild(badge);
    }

    if (sizeValues.length > CONFIG.maxBadgesPerCard) {
      const extra = document.createElement("span");
      extra.textContent = `+${sizeValues.length - CONFIG.maxBadgesPerCard}`;
      extra.setAttribute(
        "style",
        `display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;border-radius:4px;font-size:11px;font-weight:700;line-height:1.2;background:${colors.primary};color:${colors.background};`
      );
      wrap.appendChild(extra);
    }

    if (!existing) card.appendChild(wrap);
  }

  function extractPidFromUrl(url) {
    if (!url) return null;
    const match = url.match(/\/(?:produto|produtos|product|products|p)\/(\d+)/);
    return match ? match[1] : null;
  }

  async function enhanceSingleCard(card, allowSizeBadges) {
    if (!card || !card.isConnected) return null;

    if (card.getAttribute("data-tn-enhanced")) {
      // Card já processado — verifica se o Nuvemshop resetou o preço e reaplica.
      const storedPrice = parseFloat(card.getAttribute("data-tn-from-price") || "");
      if (storedPrice > 0) applyStartingFromOnCard(card, storedPrice);
      return null;
    }

    let data = null;
    let source = "none";
    const url = getCardLink(card);
    const pid = card.getAttribute("data-product-id") || extractPidFromUrl(url);

    // 1. Tenta localStorage pelo product ID — mais rápido que re-parsear atributos.
    if (pid) {
      const cached = localCache.get("pid_" + pid);
      if (cached) {
        data = cached;
        source = "ls-cache";
      }
    }

    // 2. Tenta data-variants embutido no card.
    if (!data) {
      const variantsInCard = findVariantsFromCardData(card);
      if (Array.isArray(variantsInCard) && variantsInCard.length) {
        data = getProductDataFromVariants(variantsInCard);
        source = data ? "data-variants" : "data-variants-invalid";
        if (data && pid) localCache.set("pid_" + pid, data);
      }
    }

    // 3. Fallback: fetch do HTML da página do produto.
    if (!data) {
      if (!url) return null;
      data = await fetchProductData(url);
      source = data ? "fetch" : "fetch-empty";
      if (data && pid) localCache.set("pid_" + pid, data);
    }

    if (!data) {
      debugLog("card sem dados de variantes", { url: url || null, source });
      card.setAttribute("data-tn-enhanced", "true");
      return {
        source,
        hasDifferentPrices: false,
        appliedStartingFrom: false,
        hasSizes: false
      };
    }

    let appliedStartingFrom = false;
    if (data.hasDifferentPrices) {
      applyStartingFromOnCard(card, data.minPrice);
      card.setAttribute("data-tn-from-price", String(data.minPrice));
      appliedStartingFrom = true;
    }

    const hasSizes = Array.isArray(data.sizeValues) && data.sizeValues.length >= 2;

    if (allowSizeBadges) {
      upsertSizeBadges(card, data.sizeValues);
    }

    debugLog("card processado", {
      url: url || null,
      source,
      hasDifferentPrices: !!data.hasDifferentPrices,
      appliedStartingFrom,
      hasSizes
    });

    card.setAttribute("data-tn-enhanced", "true");
    return {
      source,
      hasDifferentPrices: !!data.hasDifferentPrices,
      appliedStartingFrom,
      hasSizes
    };
  }

  async function enhanceListCards() {
    const cards = getCardsWithProductLinks();
    if (!cards.length) {
      debugLog("nenhum card encontrado na listagem");
      return;
    }

    const allowSizeBadges = !isProductPage();
    const stats = {
      cardsFound: cards.length,
      fromDataVariants: 0,
      fromFetch: 0,
      startingFromApplied: 0
    };

    const CONCURRENCY = 6;
    const queue = cards.slice();
    const processCard = async function (card) {
      const result = await enhanceSingleCard(card, allowSizeBadges);
      if (!result) return;
      if (result.source === "data-variants") stats.fromDataVariants += 1;
      if (String(result.source).startsWith("fetch")) stats.fromFetch += 1;
      if (result.appliedStartingFrom) stats.startingFromApplied += 1;
    };
    const workers = Array.from({ length: Math.min(CONCURRENCY, cards.length) }, async function () {
      while (queue.length) {
        await processCard(queue.shift());
      }
    });
    await Promise.all(workers);

    debugLog("resumo listagem", stats);
  }

  function scheduleListEnhancement() {
    if (listEnhancementState.timer) {
      window.clearTimeout(listEnhancementState.timer);
    }

    listEnhancementState.timer = window.setTimeout(function () {
      runListEnhancementNow("debounced");
    }, CONFIG.listDebounceMs);
  }

  function runListEnhancementNow(reason) {
    enhanceListCards().catch(function (error) {
      const message = error && error.message ? error.message : String(error);
      debugLog(`erro no enhanceListCards (${reason})`, message);
    });
  }

  function runInitialListLoops() {
    const loops = Math.max(0, CONFIG.initialListLoops || 0);
    if (!loops) return;

    for (let i = 0; i < loops; i += 1) {
      const delay = i * CONFIG.initialListLoopDelayMs;
      window.setTimeout(function () {
        scheduleListEnhancement();
        window.setTimeout(function () {
          runListEnhancementNow(`initial-loop-${i + 1}`);
        }, CONFIG.immediateListRunDelayMs);
      }, delay);
    }
  }

  function bootListObserver() {
    if (listEnhancementState.observer) return;
    if (!document.body) {
      window.setTimeout(bootListObserver, 120);
      return;
    }

    listEnhancementState.observer = new MutationObserver(function (mutations) {
      const hasNewNodes = mutations.some(function (m) { return m.addedNodes.length > 0; });
      if (hasNewNodes) scheduleListEnhancement();
    });

    listEnhancementState.observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  // URL do endpoint de pré-carga do backend (retorna variantes de todos os produtos em 1 request).
  var STOREFRONT_API_URL = "https://gestaopedidos.planteumaflor.online/storefront/produtos-variantes";

  async function prefetchAllProductsFromBackend() {
    try {
      var response = await fetch(STOREFRONT_API_URL, {
        method: "GET",
        credentials: "omit",
        headers: { "Accept": "application/json" }
      });
      if (!response.ok) return;
      var summary = await response.json();
      if (!summary || typeof summary !== "object") return;

      var count = 0;
      for (var pid in summary) {
        if (!Object.prototype.hasOwnProperty.call(summary, pid)) continue;
        var d = summary[pid];
        if (!d || typeof d.minPrice !== "number") continue;
        localCache.set("pid_" + pid, {
          prices: [d.minPrice],
          minPrice: d.minPrice,
          hasDifferentPrices: !!d.hasDifferentPrices,
          sizeValues: []
        });
        count += 1;
      }
      debugLog("prefetch backend concluido", { produtos: count });
    } catch (e) {
      // Falha silenciosa — cards continuarão usando fetch individual como fallback.
      debugLog("prefetch backend falhou", e && e.message ? e.message : String(e));
    }
  }

  function init() {
    window.__APARITRDE_LOADED__ = APP_SIGNATURE;
    if (window.console && typeof window.console.log === "function") {
      window.console.log("[aparitrde] loaded", APP_SIGNATURE);
    }

    if (isProductPage()) {
      bootInitialProductState();
      bootProductVariantListener();
    }

    // Pré-carrega dados de variantes de todos os produtos via backend (1 request).
    // Quando os cards aparecerem, os dados já estarão no cache → sem fetches individuais.
    prefetchAllProductsFromBackend().then(function () {
      scheduleListEnhancement();
      runListEnhancementNow("init-after-prefetch");
    });

    // Inicia o observer e loops imediatamente (não espera o prefetch).
    scheduleListEnhancement();
    runListEnhancementNow("init-immediate");
    runInitialListLoops();
    bootListObserver();
  }

  try {
    init();
  } catch (error) {
    window.__APARITRDE_ERROR__ = error && error.message ? error.message : String(error);
    if (window.console && typeof window.console.error === "function") {
      window.console.error("[aparitrde] init error", error);
    }
  }
})();
