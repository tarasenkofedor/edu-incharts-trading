<template>
  <div class="news-panel" v-if="show">
    <div class="news-panel-header">
      <h3>Quick Look: {{ symbol }} News</h3>
      <button @click="handleClosePanel" class="close-button">×</button>
    </div>
    <div class="news-panel-content">
      <div v-if="isNewsLoading" class="loading-state">
        <p>Loading news...</p>
      </div>
      <div v-else-if="newsError" class="error-state">
        <p>{{ newsError }}</p>
        <button @click="handleFetchNews">Try Again</button>
      </div>
      <div
        v-else-if="!newsArticles || !newsArticles.length"
        class="empty-state"
      >
        <p>No news available for {{ symbol }} at the moment.</p>
      </div>
      <div v-else class="articles-list">
        <div
          v-for="article in newsArticles"
          :key="article.external_article_id"
          class="article-item"
        >
          <a
            v-if="article.image_url"
            :href="article.article_url"
            target="_blank"
            rel="noopener noreferrer"
            class="article-image-link"
          >
            <img
              :src="article.image_url"
              alt="Article image"
              class="article-image"
            />
          </a>
          <div class="article-details">
            <div class="headline-sentiment-wrapper">
              <h4 class="article-headline">{{ article.headline }}</h4>
              <span
                v-if="article.sentiment_category_derived"
                class="sentiment-tag"
                :class="getSentimentClass(article.sentiment_category_derived)"
              >
                {{
                  getSentimentDisplayText(
                    article.sentiment_category_derived,
                    article.sentiment_score_external
                  )
                }}
              </span>
            </div>
            <p class="article-meta">
              <b>
                <span class="article-source">{{
                  article.source_name + " /"
                }}</span>
              </b>

              <span class="article-date">
                {{ formatDate(article.published_at) }}
              </span>
            </p>
            <p class="article-snippet">{{ article.snippet }}</p>
            <a
              :href="article.article_url"
              target="_blank"
              rel="noopener noreferrer"
              class="article-link"
            >
              Read more
            </a>
          </div>
        </div>
      </div>
    </div>
    <div class="news-panel-footer">
      <button @click="handleRefreshNews" :disabled="isNewsLoading">
        Refresh
      </button>
      <span
        v-if="
          !isNewsLoading && !newsError && newsArticles && newsArticles.length
        "
      >
        Updated: {{ lastUpdatedTimestamp }}
      </span>
      <span v-else-if="isNewsLoading">Loading...</span>
      <span v-else-if="newsError">Failed to load</span>
      <span v-else>No news</span>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from "vuex";

export default {
  name: "NewsPanel",
  props: {
    show: {
      type: Boolean,
      required: true,
    },
    symbol: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      lastUpdatedTimestamp: null, // To show a simple update time
      newsRefreshIntervalId: null, // To store the interval ID for auto-refresh
    };
  },
  computed: {
    ...mapState("news", ["newsArticles", "isNewsLoading", "newsError"]),
    loggedNewsArticles() {
      const articles = this.newsArticles;
      console.log(
        "[NewsPanel.vue COMPUTED] newsArticles is now:",
        Array.isArray(articles)
          ? JSON.parse(JSON.stringify(articles))
          : articles
      );
      return articles;
    },
  },
  methods: {
    ...mapActions("news", ["fetchNewsForSymbol", "clearNews"]),
    handleClosePanel() {
      this.clearNews(); // Dispatch action to clear news in store
      this.stopNewsRefreshTimer(); // Stop timer when panel is closed
      this.$emit("close");
    },
    async handleFetchNews() {
      if (!this.symbol || this.symbol === "N/A") {
        // Optional: could dispatch an action to set a specific 'select symbol' error in store
        return;
      }
      await this.fetchNewsForSymbol(this.symbol);
      if (!this.newsError && this.newsArticles && this.newsArticles.length) {
        this.lastUpdatedTimestamp = new Date().toLocaleTimeString();
      }
    },
    handleRefreshNews() {
      this.handleFetchNews();
    },
    startNewsRefreshTimer() {
      this.stopNewsRefreshTimer(); // Clear any existing timer first
      if (this.show && this.symbol && this.symbol !== "N/A") {
        this.newsRefreshIntervalId = setInterval(() => {
          console.log("[NewsPanel.vue] Auto-refreshing news for:", this.symbol);
          this.handleFetchNews();
        }, 5 * 60 * 1000); // 6 minutes in milliseconds
        console.log(
          `[NewsPanel.vue] News auto-refresh timer started. ID: ${this.newsRefreshIntervalId}`
        );
      }
    },
    stopNewsRefreshTimer() {
      if (this.newsRefreshIntervalId) {
        clearInterval(this.newsRefreshIntervalId);
        console.log(
          `[NewsPanel.vue] News auto-refresh timer stopped. ID: ${this.newsRefreshIntervalId}`
        );
        this.newsRefreshIntervalId = null;
      }
    },
    formatDate(dateString) {
      if (!dateString) return "";
      const options = {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      };
      return new Date(dateString).toLocaleDateString(undefined, options);
    },
    getSentimentDisplayText(category, score) {
      let catDisplay = category
        ? category.charAt(0).toUpperCase() + category.slice(1)
        : "Neutral";
      let scoreDisplay = "";

      if (typeof score === "number") {
        if (catDisplay === "Neutral") {
          // For Neutral, if a score is present, we still display (0.00) as per mockup target
          scoreDisplay = " (0.00)";
        } else {
          scoreDisplay = ` (${score >= 0 ? "+" : ""}${score.toFixed(2)})`;
        }
      } else {
        // Score is null
        if (catDisplay === "Neutral") {
          scoreDisplay = " (0.00)"; // Neutral without score also shows (0.00)
        }
        // For Positive/Negative with null score, scoreDisplay remains empty, so only category shows.
      }
      return `${catDisplay}${scoreDisplay}`.trim();
    },
    getSentimentClass(category) {
      if (!category) return "sentiment-neutral"; // Default
      const lowerCategory = category.toLowerCase();
      if (lowerCategory === "positive") return "sentiment-positive";
      if (lowerCategory === "negative") return "sentiment-negative";
      return "sentiment-neutral"; // Default for 'neutral' or any other case
    },
  },
  watch: {
    show(newValue) {
      if (newValue && this.symbol && this.symbol !== "N/A") {
        this.handleFetchNews(); // Fetch immediately when shown
        this.startNewsRefreshTimer(); // And start the timer
      } else if (!newValue) {
        this.clearNews(); // Clear news when panel is hidden
        this.stopNewsRefreshTimer(); // Stop timer when panel is hidden
      }
    },
    symbol(newSymbol, oldSymbol) {
      if (
        this.show &&
        newSymbol &&
        newSymbol !== oldSymbol &&
        newSymbol !== "N/A"
      ) {
        this.clearNews(); // Clear old news first
        this.handleFetchNews(); // Fetch for new symbol if panel is already shown
        this.startNewsRefreshTimer(); // Restart timer for the new symbol
      }
    },
    newsArticles: {
      handler(newArticles, oldArticles) {
        console.log("[NewsPanel.vue WATCHER] newsArticles changed.");
        console.log(
          "[NewsPanel.vue WATCHER] New articles:",
          Array.isArray(newArticles)
            ? JSON.parse(JSON.stringify(newArticles))
            : newArticles
        );
        if (oldArticles) {
          console.log(
            "[NewsPanel.vue WATCHER] Old articles:",
            Array.isArray(oldArticles)
              ? JSON.parse(JSON.stringify(oldArticles))
              : oldArticles
          );
        }
        const currentArticles = this.newsArticles;
        const len = Array.isArray(currentArticles)
          ? currentArticles.length
          : currentArticles === null
          ? "null"
          : "undefined";
        console.log(`[NewsPanel.vue WATCHER] Current length: ${len}`);
      },
      deep: true,
    },
  },
  updated() {
    console.log("[NewsPanel.vue UPDATED hook] Component updated.");
    const articles = this.newsArticles;
    console.log(
      "[NewsPanel.vue UPDATED hook] this.newsArticles:",
      Array.isArray(articles) ? JSON.parse(JSON.stringify(articles)) : articles
    );
    const updatedArticles = this.newsArticles;
    console.log(
      "[NewsPanel.vue UPDATED hook] this.newsArticles length:",
      Array.isArray(updatedArticles)
        ? updatedArticles.length
        : updatedArticles === null
        ? "null"
        : "undefined"
    );
  },
  mounted() {
    console.log("[NewsPanel.vue MOUNTED hook] Component mounted.");
    const articles = this.newsArticles;
    console.log(
      "[NewsPanel.vue MOUNTED hook] this.newsArticles:",
      Array.isArray(articles) ? JSON.parse(JSON.stringify(articles)) : articles
    );
    const mountedArticles = this.newsArticles;
    console.log(
      "[NewsPanel.vue MOUNTED hook] this.newsArticles length:",
      Array.isArray(mountedArticles)
        ? mountedArticles.length
        : mountedArticles === null
        ? "null"
        : "undefined"
    );
  },
  beforeDestroy() {
    this.stopNewsRefreshTimer(); // Ensure timer is stopped when component is destroyed
  },
};
</script>

<style scoped>
.news-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 350px; /* Adjust width as needed */
  height: 100vh;
  background-color: #2f3136; /* Dark background */
  border-left: 1px solid #4f545c; /* Darker border */
  box-shadow: -2px 0 5px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  z-index: 1000; /* Ensure it's above other content */
  padding: 10px;
  box-sizing: border-box;
  color: #dcddde; /* Light text color */
}

.news-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid #202225; /* Darker border */
  margin-bottom: 10px;
}

.news-panel-header h3 {
  margin: 0;
  font-size: 1.1em;
  color: #ffffff; /* White title */
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5em;
  color: #b9bbbe; /* Lighter gray for close icon */
  cursor: pointer;
  padding: 0 5px;
}
.close-button:hover {
  color: #ffffff;
}

.news-panel-content {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 5px; /* For scrollbar spacing */
}

.loading-state p,
.error-state p,
.empty-state p {
  text-align: center;
  padding: 20px;
  color: #8e9297; /* Mid-gray text for states */
}

.error-state button {
  display: block;
  margin: 10px auto;
  padding: 8px 15px;
  background-color: #7289da; /* Discord blue/purple */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.error-state button:hover {
  background-color: #677bc4;
}

.articles-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.article-item {
  background-color: #36393f; /* Darker item background */
  border: 1px solid #4f545c; /* Item border */
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column; /* Stack image above details */
  gap: 10px;
}

.article-image {
  width: 100%;
  max-height: 180px; /* Limit image height */
  object-fit: cover; /* Crop image nicely */
  border-radius: 4px;
  margin-bottom: 8px; /* Space between image and text if image is on top */
}

.article-details {
  display: flex;
  flex-direction: column;
}

.headline-sentiment-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: flex-start; /* Or center if preferred */
  margin-bottom: 5px; /* Space below this wrapper */
}

.article-headline {
  font-size: 1em;
  font-weight: 600;
  color: #ffffff; /* White headline */
  margin: 0; /* Remove default h4 margin */
  flex-grow: 1; /* Allow headline to take available space */
  padding-right: 10px; /* Add some space before sentiment tag if headline is long */
}

.article-meta {
  font-size: 0.8em;
  color: #b9bbbe; /* Lighter gray for meta */
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.article-source {
  font-size: 1.1em;
  margin-right: 5px;
  color: #8e9297; /* Mid-gray for source */
}

.article-date {
  font-style: italic;
  /* margin-right: 8px; Removed as sentiment tag is no longer here */
}

.sentiment-tag {
  font-size: 0.85em; /* Adjusted for placement next to headline */
  padding: 3px 8px; /* Slightly increased padding for a better pill shape */
  border-radius: 12px; /* More pill-like */
  font-weight: 500;
  color: white; /* Default to white, specific classes will apply BG */
  white-space: nowrap; /* Prevent tag from wrapping */
  /* margin-left: 5px; Removed, alignment handled by flex parent */
}

/* Adjusted sentiment colors for dark theme visibility */
.sentiment-positive {
  background-color: rgba(76, 175, 80, 0.2); /* Green with low opacity */
  color: #4caf50;
  font-weight: bold;
}

.sentiment-neutral {
  background-color: rgba(176, 190, 197, 0.2); /* Blue-gray with low opacity */
  color: #b0bec5;
  font-weight: bold;
}

.sentiment-negative {
  background-color: rgba(244, 67, 54, 0.2); /* Red with low opacity */
  color: #f44336;
  font-weight: bold;
}

.article-snippet {
  font-size: 0.9em;
  color: #dcddde; /* Light gray for snippet */
  margin-bottom: 8px;
  line-height: 1.4;
}

.article-link {
  font-size: 0.9em;
  color: #7289da; /* Discord blue/purple for links */
  text-decoration: none;
  align-self: flex-end;
}

.article-link:hover {
  text-decoration: underline;
  color: #8a9ef0;
}

/* Optional: Add a simple scrollbar style */
.news-panel-content::-webkit-scrollbar {
  width: 8px;
}

.news-panel-content::-webkit-scrollbar-thumb {
  background-color: #4f545c;
  border-radius: 4px;
}

.news-panel-content::-webkit-scrollbar-track {
  background-color: #2f3136;
}
.news-panel-content::-webkit-scrollbar-thumb:hover {
  background-color: #5c6168;
}

.news-panel-footer {
  padding-top: 10px;
  border-top: 1px solid #202225; /* Darker border */
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
  color: #b9bbbe; /* Lighter gray for footer text */
}

.news-panel-footer button {
  padding: 5px 10px;
  border: 1px solid #4f545c;
  background-color: #4a4d52; /* Darker button */
  color: #ffffff;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}
.news-panel-footer button:hover:not(:disabled) {
  background-color: #585b60;
}

.news-panel-footer button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: #3a3c40;
  color: #72767d;
}
</style>
