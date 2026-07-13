/**
 * VeroRAG — Knowledge Base Search SDK for Social Media Mini-Programs
 * 
 * Queries the VeroRun RAG (Retrieval-Augmented Generation) knowledge base
 * to retrieve relevant context for AI responses.
 * 
 * @module sdks/common/rag
 */

class VeroRAG {

    /**
     * @param {Object} config
     * @param {string} config.baseURL - System base URL
     * @param {string} config.token   - JWT token
     */
    constructor(config) {
        this.baseURL = config.baseURL;
        this.token = config.token;
    }

    /**
     * Search the knowledge base.
     * 
     * @param {string} query - Search query string
     * @param {number} [topK=5] - Number of results to return
     * @param {string|null} [category=null] - Optional category filter
     * @returns {Promise<Object>} { success, data: [{ id, title, content, score, category }] }
     */
    async search(query, topK = 5, category = null) {
        const params = new URLSearchParams({ q: query, topK: String(topK) });
        if (category) params.set('category', category);
        const res = await fetch(
            `${this.baseURL}/api/v1/mini-program/knowledge/search?${params}`,
            { headers: { 'Authorization': `Bearer ${this.token}` } }
        );
        return res.json();
    }

    /**
     * Get site information (brand, theme tokens).
     * 
     * @returns {Promise<Object>} { success, data: { site_name, primary_color, logo_url, ... } }
     */
    async getSiteInfo() {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/site/info`);
        return res.json();
    }

    /**
     * Get published page list.
     * 
     * @returns {Promise<Object>} { success, data: [{ slug, title, ... }] }
     */
    async getPages() {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/site/pages`);
        return res.json();
    }

    /**
     * Get a specific page by slug.
     * 
     * @param {string} slug - Page slug
     * @returns {Promise<Object>} { success, data: { slug, title, blocks: [...] } }
     */
    async getPage(slug) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/site/page/${encodeURIComponent(slug)}`);
        return res.json();
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VeroRAG };
}