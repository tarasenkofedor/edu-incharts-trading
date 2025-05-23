<template>
  <div class="home-container">
    <div class="top-controls">
      <div class="mode-asset-controls">
        <router-link to="/" class="home-link header-button">Home</router-link>
        <!-- Asset/Timeframe Selector -->
        <AssetTimeframeSelector
          :asset="vuexCurrentDisplayAsset"
          :timeframe="vuexCurrentDisplayTimeframeUserSelected"
          :available-timeframes="availableTimeframesForSelector"
          @asset-updated="handleAssetUpdate"
          @timeframe-updated="handleTimeframeUpdate"
        />
        <!-- Live/Custom Chart buttons next -->
        <div class="mode-buttons-inline-container">
          <button
            @click="switchToLiveMode"
            :class="{ active: currentChartMode === 'live' }"
            class="mode-button"
          >
            Live Chart
          </button>
          <button
            @click="switchToCustomMode"
            :class="{ active: currentChartMode === 'custom' }"
            class="mode-button"
          >
            Custom Chart
          </button>
        </div>
      </div>

      <!-- user-controls div restored for top-right elements -->
      <div class="user-controls">
        <button
          v-if="isAuthenticated"
          @click="toggleNewsPanel"
          class="news-toggle-button header-button"
          title="Toggle News Panel"
        >
          📰 News
        </button>
        <button
          v-if="isAuthenticated"
          @click="togglePerflogsPanel"
          class="perflogs-toggle-button header-button"
          title="Toggle Performance Logs"
        >
          📈 Perflogs
        </button>
        <span v-if="isAuthenticated && currentUser" class="user-greeting">
          Hello, <b>{{ currentUser.nickname }}!</b>
        </span>
        <button
          v-if="isAuthenticated"
          @click="handleLogout"
          class="logout-button header-button"
        >
          Log out
        </button>
        <!-- New Log in Button -->
        <router-link
          v-if="!isAuthenticated"
          to="/login"
          class="login-button header-button"
        >
          Log in
        </router-link>
      </div>
    </div>

    <div class="controls-container">
      <div class="uploaders-container">
        <csv-upload
          v-if="currentChartMode === 'custom'"
          ref="csvUploader"
          @file-upload-initiated="initiateUpload"
          class="uploader-component"
        />
        <signal-upload
          v-if="currentChartMode === 'live' || currentChartMode === 'custom'"
          ref="signalUploader"
          @signal-data-uploaded="handleSignalData"
          class="uploader-component"
        />
        <!-- Add a placeholder if no uploader is visible to maintain layout integrity -->
        <div
          v-if="currentChartMode !== 'custom' && currentChartMode !== 'live'"
          class="uploader-placeholder"
        ></div>
      </div>
    </div>

    <div class="chart-status-indicators" v-if="currentChartMode === 'live'">
      <div v-if="isInitialLiveLoading" class="status-message loading-message">
        Loading initial live chart data for {{ vuexCurrentDisplayAsset }}/{{
          vuexCurrentDisplayTimeframeUserSelected
        }}...
      </div>
      <div
        v-if="isLoadingMoreHistory && !isInitialLiveLoading"
        class="status-message loading-message"
      >
        Loading more historical data...
      </div>
      <div
        v-if="
          currentBackfillStatus && currentBackfillStatus.includes('in_progress')
        "
        class="status-message backfill-message"
      >
        Data backfill for {{ vuexCurrentDisplayAsset }}/{{
          vuexCurrentDisplayTimeframeUserSelected
        }}
        is {{ currentBackfillStatus.replace("_", " ") }}. Chart may be
        incomplete.
        <span v-if="currentBackfillTimestamp">
          (Last update:
          {{ new Date(currentBackfillTimestamp).toLocaleString() }})</span
        >
      </div>
    </div>

    <div class="chart-container">
      <trading-vue
        ref="tradingVue"
        :data="chartDataCubeFromStore"
        :width="this.width"
        :height="this.height"
        :overlays="chartOverlays"
        :key="chartResetKey"
        @range-changed="handleRangeChange"
      />
    </div>
    <ChartStatusPopup ref="chartStatusPopup" :autoDismissDelay="7000" />

    <!-- Conditionally render NewsPanel -->
    <news-panel
      :show="showNewsPanel"
      :symbol="vuexCurrentDisplayAsset"
      @close="closeNewsPanel"
      @refresh="refreshNewsData"
    />
    <!-- Conditionally render PerflogsPanel -->
    <perflogs-panel
      :show="showPerflogsPanel"
      :asset-ticker="vuexCurrentDisplayAsset"
      :asset-timeframe="vuexCurrentDisplayTimeframeUserSelected"
      @close-panel="closePerflogsPanel"
    />
  </div>
</template>

<script>
import { mapGetters, mapActions } from "vuex";
import axios from "axios";
import TradingVue from "../trading-vue-core/TradingVue.vue";
import CsvUpload from "../components/CsvUpload.vue";
import SignalUpload from "../components/SignalUpload.vue";
import TradesOverlay from "../trading-vue-core/components/overlays/Trades.vue";
import ChartStatusPopup from "../components/ChartStatusPopup.vue";
import NewsPanel from "../components/NewsPanel.vue";
import PerflogsPanel from "../components/PerflogsPanel.vue";
import AssetTimeframeSelector from "../components/AssetTimeframeSelector.vue";

export default {
  name: "HomeViewPage",
  components: {
    TradingVue,
    CsvUpload,
    SignalUpload,
    ChartStatusPopup,
    NewsPanel,
    PerflogsPanel,
    AssetTimeframeSelector,
  },
  data() {
    return {
      width: window.innerWidth * 0.9,
      height: window.innerHeight * 0.7,
      chartResetKey: 0,
      ohlcvDataLoaded: false,
      chartOverlays: [TradesOverlay],
      isLoadingMoreHistory: false,
      oldestKlineTimestampLoaded: null,
      loadMoreThresholdFactor: 3,
      livePriceSocket: null,
      socketReconnectDelay: 5000,
      socketMaxReconnectAttempts: 5,
      socketReconnectAttempts: 0,
      currentBackfillStatus: null,
      currentBackfillTimestamp: null,
      isInitialLiveLoading: false,
      showNewsPanel: false,
      showPerflogsPanel: false,
      availableTimeframesForSelector: [],
    };
  },
  computed: {
    ...mapGetters("chart", {
      chartDataCubeFromStore: "getChartDataCube",
      chartMode: "getChartMode",
      lastLiveAsset: "getLastLiveAsset",
      lastLiveTimeframe: "getLastLiveTimeframe",
      vuexCurrentDisplayAsset: "getCurrentDisplayAsset",
      vuexCurrentDisplayTimeframeUserSelected:
        "getCurrentDisplayTimeframeUserSelected",
    }),
    isAuthenticated() {
      return this.$store.getters["auth/isLoggedIn"];
    },
    currentUser() {
      return this.$store.getters["auth/authUser"];
    },
    currentChartMode() {
      return this.chartMode;
    },
    currentDisplaySymbol() {
      return this.vuexCurrentDisplayAsset;
    },
    currentDisplayTimeframe() {
      return this.vuexCurrentDisplayTimeframeUserSelected;
    },
    currentContextIdentifier() {
      return `${this.vuexCurrentDisplayAsset}-${this.vuexCurrentDisplayTimeframeUserSelected}`;
    },
  },
  methods: {
    ...mapActions("chart", [
      "loadInitialChartData",
      "setUploadedChartData",
      "addSignalOverlays",
      "setChartMode",
      "setLiveChartData",
      "prependHistoricalKlines",
      "updateLiveKline",
      "updateCurrentDisplayAsset",
      "updateCurrentDisplayTimeframeUserSelected",
      "resetChartForNewContext",
      "setLastLiveAssetAndTimeframe",
    ]),
    ...mapActions("auth", ["logout"]),
    ...mapActions("perflogs", ["setCurrentAssetContext", "clearPerflogsData"]),
    ...mapActions("news", ["clearNews"]),
    switchToLiveMode() {
      this.setChartMode("live");
      this.clearNews();
    },
    switchToCustomMode() {
      this.setChartMode("custom");
      this.clearNews();
    },
    handleResize() {
      const chartContainer = this.$el.querySelector(".chart-container");
      if (chartContainer) {
        this.width = chartContainer.offsetWidth;
        this.height = chartContainer.offsetHeight;
      } else {
        this.width = window.innerWidth;
        this.height = window.innerHeight - 200;
      }
      this.chartResetKey++;
    },
    async initiateUpload(file) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await axios.post(
          "http://localhost:8000/data/upload_csv",
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
            },
          }
        );

        if (response.data && response.data.chartData) {
          const newChartData = response.data.chartData;
          this.setUploadedChartData(newChartData);
          this.$refs.csvUploader.setUploadStatus(
            false,
            `Successfully uploaded: ${file.name}. Chart updated.`,
            "success"
          );
        } else {
          this.$refs.csvUploader.setUploadStatus(
            false,
            "No chart data received from backend.",
            "error"
          );
        }
      } catch (error) {
        let errorMessage =
          "Error uploading file. Please ensure it is a valid OHLCV CSV.";
        if (
          error.response &&
          error.response.data &&
          error.response.data.detail
        ) {
          errorMessage =
            typeof error.response.data.detail === "string"
              ? error.response.data.detail
              : JSON.stringify(error.response.data.detail);
        }

        this.$refs.csvUploader.setUploadStatus(false, errorMessage, "error");

        if (
          !error.response ||
          (error.response.status !== 400 && error.response.status !== 422)
        ) {
          console.error(
            "[Home.vue] An unexpected error occurred during CSV upload:",
            error
          );
        }
      }
    },
    handleSignalData(processedSignals) {
      if (processedSignals && processedSignals.length > 0) {
        let previousVisibleStartTime = null;
        let previousVisibleEndTime = null;
        if (this.$refs.tradingVue && this.$refs.tradingVue.getRange) {
          const currentRange = this.$refs.tradingVue.getRange();
          if (currentRange && currentRange.length === 2) {
            previousVisibleStartTime = currentRange[0];
            previousVisibleEndTime = currentRange[1];
          }
        }

        this.addSignalOverlays(processedSignals);
        this.chartResetKey++;

        this.$nextTick(() => {
          if (this.$refs.tradingVue) {
            if (
              previousVisibleStartTime !== null &&
              previousVisibleEndTime !== null
            ) {
              if (typeof this.$refs.tradingVue.setRange === "function") {
                console.log(
                  "[Home.vue] Attempting to restore range after signal add and chart reset:",
                  new Date(previousVisibleStartTime).toISOString(),
                  new Date(previousVisibleEndTime).toISOString()
                );
                this.$refs.tradingVue.setRange(
                  previousVisibleStartTime,
                  previousVisibleEndTime
                );
              } else {
                console.warn(
                  "[Home.vue] $refs.tradingVue.setRange is not a function after chart reset."
                );
              }
            } else {
              console.warn(
                "[Home.vue] Previous range not captured, cannot restore after signal add."
              );
            }
          } else {
            console.warn(
              "[Home.vue] $refs.tradingVue not available in $nextTick after chart reset."
            );
          }
        });
      } else {
        console.warn(
          "[Home.vue] handleSignalData: No processed signals to add."
        );
      }
    },
    async fetchInitialHistoricalKlines() {
      if (
        !this.vuexCurrentDisplayAsset ||
        !this.vuexCurrentDisplayTimeframeUserSelected
      ) {
        console.error(
          "[Home.vue] Missing asset or timeframe for historical data fetch."
        );
        this.oldestKlineTimestampLoaded = null;
        return;
      }
      console.log(
        `[Home.vue] Fetching initial historical klines for ${this.vuexCurrentDisplayAsset} ${this.vuexCurrentDisplayTimeframeUserSelected}`
      );
      this.isLoadingMoreHistory = true;
      this.isInitialLiveLoading = true;
      this.currentBackfillStatus = null;
      this.currentBackfillTimestamp = null;
      try {
        const params = {
          limit: 300,
        };
        const response = await axios.get(
          `http://localhost:8000/data/klines/${this.vuexCurrentDisplayAsset}/${this.vuexCurrentDisplayTimeframeUserSelected}`,
          { params }
        );

        if (
          response.data &&
          response.data.klines &&
          response.data.klines.length > 0
        ) {
          const klinesFromApi = response.data.klines;
          const klinesAsArrays = klinesFromApi.map((k) => [
            k.open_time,
            k.open_price,
            k.high_price,
            k.low_price,
            k.close_price,
            k.volume,
          ]);

          this.setLiveChartData(klinesAsArrays);
          this.oldestKlineTimestampLoaded = klinesAsArrays[0][0];
          console.log(
            `[Home.vue] Loaded ${
              klinesAsArrays.length
            } historical klines. Oldest: ${new Date(
              this.oldestKlineTimestampLoaded
            ).toISOString()}`
          );
          if (response.data.backfill_status) {
            console.log(
              `[Home.vue] Backfill status for ${this.vuexCurrentDisplayAsset} ${this.vuexCurrentDisplayTimeframeUserSelected}: ${response.data.backfill_status}, updated: ${response.data.backfill_last_updated_ts}`
            );
            this.currentBackfillStatus = response.data.backfill_status;
            this.currentBackfillTimestamp =
              response.data.backfill_last_updated_ts;
          }
          this.$nextTick(() => {
            if (this.$refs.tradingVue && klinesAsArrays.length > 0) {
              const lastTimestamp =
                klinesAsArrays[klinesAsArrays.length - 1][0];
              const firstTimestamp = klinesAsArrays[0][0];
              const range = lastTimestamp - firstTimestamp;
              const padding = range > 0 ? range * 0.1 : 60000 * 30;
              this.$refs.tradingVue.setRange(
                firstTimestamp - padding,
                lastTimestamp + padding
              );
            }
            this.chartResetKey++;
          });
        } else {
          console.warn(
            "[Home.vue] No klines received from initial historical data fetch."
          );
          this.oldestKlineTimestampLoaded = null;
          this.setLiveChartData([]);
        }
      } catch (error) {
        console.error(
          `[Home.vue] Error fetching initial historical klines for ${this.vuexCurrentDisplayAsset} ${this.vuexCurrentDisplayTimeframeUserSelected}:`,
          error.response ? error.response.data : error.message
        );
        this.oldestKlineTimestampLoaded = null;
      } finally {
        this.isLoadingMoreHistory = false;
        this.isInitialLiveLoading = false;
      }
    },
    handleRangeChange([visibleStartTime]) {
      if (
        this.currentChartMode === "live" &&
        !this.isLoadingMoreHistory &&
        this.oldestKlineTimestampLoaded !== null &&
        this.chartDataCubeFromStore &&
        this.chartDataCubeFromStore.ohlcv &&
        this.chartDataCubeFromStore.ohlcv.length > 0
      ) {
        let currentIntervalMs = 60000;
        if (this.$refs.tradingVue && this.$refs.tradingVue.interval_ms) {
          currentIntervalMs = this.$refs.tradingVue.interval_ms;
        }

        if (
          visibleStartTime <=
          this.oldestKlineTimestampLoaded +
            currentIntervalMs * this.loadMoreThresholdFactor
        ) {
          console.log(
            "[Home.vue] Approaching oldest data edge, fetching more history..."
          );
          this.fetchOlderHistoricalKlines();
        }
      }
    },
    async fetchOlderHistoricalKlines() {
      if (
        !this.vuexCurrentDisplayAsset ||
        !this.vuexCurrentDisplayTimeframeUserSelected ||
        this.oldestKlineTimestampLoaded === null
      ) {
        console.warn(
          "[Home.vue] Cannot fetch older klines: missing asset, timeframe, or oldest timestamp."
        );
        return;
      }
      console.log(
        `[Home.vue] Fetching older historical klines for ${
          this.vuexCurrentDisplayAsset
        } ${
          this.vuexCurrentDisplayTimeframeUserSelected
        }, ending before ${new Date(
          this.oldestKlineTimestampLoaded
        ).toISOString()}`
      );
      this.isLoadingMoreHistory = true;
      try {
        let previousVisibleEndTime = null;
        let previousVisibleDuration = null;

        if (this.$refs.tradingVue && this.$refs.tradingVue.getRange) {
          const currentRange = this.$refs.tradingVue.getRange();
          if (currentRange && currentRange.length === 2) {
            previousVisibleEndTime = currentRange[1];
            previousVisibleDuration = currentRange[1] - currentRange[0];
          }
        }

        const params = {
          limit: 200,
          end_ms: this.oldestKlineTimestampLoaded - 1,
        };
        const response = await axios.get(
          `http://localhost:8000/data/klines/${this.vuexCurrentDisplayAsset}/${this.vuexCurrentDisplayTimeframeUserSelected}`,
          { params }
        );

        if (
          response.data &&
          response.data.klines &&
          response.data.klines.length > 0
        ) {
          const klinesAsArrays = response.data.klines.map((k) => [
            k.open_time,
            k.open_price,
            k.high_price,
            k.low_price,
            k.close_price,
            k.volume,
          ]);

          await this.prependHistoricalKlines(klinesAsArrays);

          const newOldestTimestamp = klinesAsArrays[0][0];

          this.oldestKlineTimestampLoaded = newOldestTimestamp;
          console.log(
            `[Home.vue] Prepended ${
              klinesAsArrays.length
            } older klines. New oldest: ${new Date(
              this.oldestKlineTimestampLoaded
            ).toISOString()}`
          );

          this.$nextTick(() => {
            if (this.$refs.tradingVue && this.$refs.tradingVue.setRange) {
              if (
                previousVisibleEndTime !== null &&
                previousVisibleDuration !== null &&
                previousVisibleDuration > 0
              ) {
                let newVisibleStartTime =
                  previousVisibleEndTime - previousVisibleDuration;
                newVisibleStartTime = Math.max(
                  this.oldestKlineTimestampLoaded,
                  newVisibleStartTime
                );

                this.$refs.tradingVue.setRange(
                  newVisibleStartTime,
                  previousVisibleEndTime
                );
              } else {
                const firstTimestamp = this.oldestKlineTimestampLoaded;
                const lastTimestamp =
                  klinesAsArrays.length > 0
                    ? klinesAsArrays[klinesAsArrays.length - 1][0]
                    : firstTimestamp + 60000 * 200;
                this.$refs.tradingVue.setRange(firstTimestamp, lastTimestamp);
                console.warn(
                  "[Home.vue] Fallback range set after prepending data due to missing previous range info."
                );
              }
            }
          });
          if (response.data.backfill_status) {
            this.currentBackfillStatus = response.data.backfill_status;
            this.currentBackfillTimestamp =
              response.data.backfill_last_updated_ts;
          }
        } else {
          console.log("[Home.vue] No more older historical klines found.");
        }
      } catch (error) {
        console.error(
          `[Home.vue] Error fetching older historical klines for ${this.vuexCurrentDisplayAsset} ${this.vuexCurrentDisplayTimeframeUserSelected}:`,
          error.response ? error.response.data : error.message
        );
      } finally {
        this.isLoadingMoreHistory = false;
      }
    },
    connectLivePriceSocket() {
      if (
        this.livePriceSocket &&
        this.livePriceSocket.readyState === WebSocket.OPEN
      ) {
        console.log("[Home.vue] WebSocket already connected.");
        return;
      }

      if (
        !this.vuexCurrentDisplayAsset ||
        !this.vuexCurrentDisplayTimeframeUserSelected
      ) {
        console.error(
          "[Home.vue] Cannot connect WebSocket: Missing asset or timeframe."
        );
        return;
      }

      const wsUrl = `ws://localhost:8000/data/ws/klines/${this.vuexCurrentDisplayAsset}/${this.vuexCurrentDisplayTimeframeUserSelected}`;
      console.log(`[Home.vue] Connecting to WebSocket: ${wsUrl}`);

      this.livePriceSocket = new WebSocket(wsUrl);

      this.livePriceSocket.onopen = () => {
        console.log(`[Home.vue] WebSocket connected to ${wsUrl}`);
        this.socketReconnectAttempts = 0;
      };

      this.livePriceSocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          // console.log("[WebSocket] Received message:", message); // General log for all messages

          if (message && message.type && message.data) {
            if (message.type === "kline_tick") {
              // console.log("[WebSocket] Processing kline_tick:", message.data);
              this.$store.dispatch("chart/processLiveKlineTick", message.data);
            } else if (message.type === "kline_closed") {
              // console.log("[WebSocket] Processing kline_closed:", message.data);
              this.$store.dispatch("chart/updateLiveKline", message.data);
            } else {
              console.warn(
                "[WebSocket] Received unknown message type:",
                message.type,
                message
              );
            }
          } else {
            console.warn(
              "[WebSocket] Received message with unexpected structure or non-kline update:",
              message
            );
          }
        } catch (error) {
          console.error(
            "[WebSocket] Error processing message:",
            error,
            "Raw data:",
            event.data
          );
        }
      };

      this.livePriceSocket.onerror = (error) => {
        console.error("[Home.vue] WebSocket error:", error);
      };

      this.livePriceSocket.onclose = (event) => {
        console.log(
          "[Home.vue] WebSocket closed. Code:",
          event.code,
          "Reason:",
          event.reason,
          "Clean:",
          event.wasClean
        );
        this.livePriceSocket = null;
        if (
          this.currentChartMode === "live" &&
          !event.wasClean &&
          event.code !== 1000
        ) {
          this.handleSocketReconnect();
        }
      };
    },

    handleSocketReconnect() {
      if (this.socketReconnectAttempts < this.socketMaxReconnectAttempts) {
        this.socketReconnectAttempts++;
        console.log(
          `[Home.vue] Attempting WebSocket reconnect ${
            this.socketReconnectAttempts
          }/${this.socketMaxReconnectAttempts} in ${
            this.socketReconnectDelay / 1000
          }s...`
        );
        setTimeout(() => {
          if (this.currentChartMode === "live") {
            this.connectLivePriceSocket();
          }
        }, this.socketReconnectDelay);
      } else {
        console.error(
          "[Home.vue] WebSocket maximum reconnect attempts reached."
        );
      }
    },

    disconnectLivePriceSocket() {
      if (this.livePriceSocket) {
        console.log("[Home.vue] Closing WebSocket connection.");
        this.livePriceSocket.close(1000);
        this.livePriceSocket = null;
      }
      this.socketReconnectAttempts = 0;
    },
    handleLogout() {
      this.logout().then(() => {
        this.$router.push("/login");
      });
    },
    toggleNewsPanel() {
      this.showNewsPanel = !this.showNewsPanel;
    },
    closeNewsPanel() {
      this.showNewsPanel = false;
    },
    refreshNewsData() {
      console.log(
        "[Home.vue] Refresh news requested for symbol:",
        this.vuexCurrentDisplayAsset
      );
    },
    openPerflogsPanel() {
      if (
        this.vuexCurrentDisplayAsset &&
        this.vuexCurrentDisplayAsset !== "N/A"
      ) {
        this.showPerflogsPanel = true;
      } else {
        this.$refs.chartStatusPopup?.show(
          "Please select an asset on the chart first.",
          "warning"
        );
        console.warn("Perflogs: No asset selected or asset is N/A.");
      }
    },
    closePerflogsPanel() {
      this.showPerflogsPanel = false;
    },
    togglePerflogsPanel() {
      if (this.showPerflogsPanel) {
        this.closePerflogsPanel();
      } else {
        this.openPerflogsPanel();
      }
    },
    handleAssetUpdate(newAsset) {
      console.log("[Home.vue] Asset updated via selector:", newAsset);
      this.updateCurrentDisplayAsset(newAsset);
    },
    handleTimeframeUpdate(newTimeframe) {
      console.log("[Home.vue] Timeframe updated via selector:", newTimeframe);
      this.updateCurrentDisplayTimeframeUserSelected(newTimeframe);
    },
    async handleAssetOrTimeframeChange(newContext, oldContext) {
      console.log(
        `[Home.vue] Context changed from ${oldContext} to ${newContext}. Evaluating changes.`
      );

      const getAssetFromContext = (contextStr) => {
        if (!contextStr || typeof contextStr !== "string") return null;
        return contextStr.split("-")[0];
      };

      const previousAsset = getAssetFromContext(oldContext);
      const currentAsset = getAssetFromContext(newContext);

      console.log(
        `[Home.vue] Previous Asset: ${previousAsset}, Current Asset: ${currentAsset}`
      );

      // Always reset chart data for any context change (asset or timeframe)
      await this.resetChartForNewContext();

      // Only clear News and Perflogs if the ASSET itself has changed
      if (previousAsset !== currentAsset) {
        console.log(
          "[Home.vue] Asset changed. Clearing News and Perflogs data."
        );
        this.clearNews();
        this.clearPerflogsData();
      } else {
        console.log(
          "[Home.vue] Asset did not change. News and Perflogs data preserved."
        );
      }

      if (this.currentChartMode === "live") {
        this.disconnectLivePriceSocket();
        await this.fetchInitialHistoricalKlines();
        this.connectLivePriceSocket();
      }

      this.chartResetKey++;
      console.log(
        "[Home.vue] Chart reset key incremented after context change."
      );
    },
    async fetchAvailableTimeframes() {
      try {
        const response = await axios.get(
          "http://localhost:8000/api/config/proactive-timeframes"
        );
        this.availableTimeframesForSelector = response.data || [];
        console.log(
          "[Home.vue] Available timeframes fetched:",
          this.availableTimeframesForSelector
        );
      } catch (error) {
        console.error("[Home.vue] Error fetching available timeframes:", error);
        this.availableTimeframesForSelector = [];
      }
    },
  },
  mounted() {
    this.$nextTick(() => {
      this.handleResize();
    });
    window.addEventListener("resize", this.handleResize);
    this.loadInitialChartData();
    this.fetchAvailableTimeframes();
  },
  beforeDestroy() {
    window.removeEventListener("resize", this.handleResize);
    this.disconnectLivePriceSocket();
  },
  watch: {
    currentChartMode(newMode, oldMode) {
      console.log(
        `[Home.vue] Chart mode changed from ${oldMode} to ${newMode}`
      );
      this.chartResetKey++;

      this.isInitialLiveLoading = false;
      this.isLoadingMoreHistory = false;
      this.currentBackfillStatus = null;
      this.currentBackfillTimestamp = null;

      if (newMode === "live") {
        const currentLiveData =
          this.chartDataCubeFromStore.data?.chart?.data ?? [];

        if (currentLiveData.length === 0) {
          this.fetchInitialHistoricalKlines();
        } else {
          this.oldestKlineTimestampLoaded = currentLiveData[0][0];
          console.log(
            `[Home.vue] Switched to LIVE mode. Using existing data for ${
              this.vuexCurrentDisplayAsset
            }/${this.vuexCurrentDisplayTimeframeUserSelected}. Oldest: ${
              this.oldestKlineTimestampLoaded
                ? new Date(this.oldestKlineTimestampLoaded).toISOString()
                : "N/A"
            }`
          );
          this.$nextTick(() => {
            if (
              this.$refs.tradingVue &&
              typeof this.$refs.tradingVue.setRange === "function"
            ) {
              const firstTimestamp = currentLiveData[0][0];
              const lastTimestamp =
                currentLiveData[currentLiveData.length - 1][0];
              const range = lastTimestamp - firstTimestamp;
              const padding = range > 0 ? range * 0.1 : 60000 * 30;
              this.$refs.tradingVue.setRange(
                firstTimestamp - padding,
                lastTimestamp + padding
              );
            }
          });
        }
        this.connectLivePriceSocket();
      } else if (newMode === "custom") {
        this.disconnectLivePriceSocket();
        const customData = this.chartDataCubeFromStore.data?.chart?.data ?? [];
        if (customData.length > 0) {
          this.$nextTick(() => {
            if (
              this.$refs.tradingVue &&
              typeof this.$refs.tradingVue.setRange === "function"
            ) {
              const firstTimestamp = customData[0][0];
              const lastTimestamp = customData[customData.length - 1][0];
              const range = lastTimestamp - firstTimestamp;
              const padding = range > 0 ? range * 0.1 : 60000 * 30;
              this.$refs.tradingVue.setRange(
                firstTimestamp - padding,
                lastTimestamp + padding
              );
            }
          });
        }
        console.log(
          "[Home.vue] Switched to CUSTOM mode. Preserved custom chart data should be displayed."
        );
      }
    },
    currentContextIdentifier: {
      handler: "handleAssetOrTimeframeChange",
    },
  },
};
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  /* background-color: #f0f2f5; */
}

.top-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background-color: #ffffff;
  border-bottom: 1px solid #dcdcdc;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.home-link {
  margin-right: 15px;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 5px;
  background-color: #6c757d;
  color: #ffffff;
  font-weight: 500;
  /* transition: background-color 0.2s ease-in-out, transform 0.2s ease-in-out; */
}

.home-link:hover {
  background-color: #5a6268;
  /* transform: translateY(-1px); */
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.mode-asset-controls {
  display: flex;
  align-items: center;
  gap: 15px;
}

.mode-buttons-inline-container {
  display: flex;
  gap: 10px;
  margin-left: 10px;
}

.user-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-greeting {
  font-size: 0.9em;
  color: #333;
  margin-left: 5px;
  margin-right: 5px;
}

.header-button {
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.9em;
  background-color: #f0f0f0;
  /* background-color: #f0f0f0; */
  color: #333;
  transition: background-color 0.3s ease, color 0.3s ease,
    border-color 0.3s ease;
}

.header-button:hover {
  background-color: #e0e0e0;
  border-color: #c0c0c0;
}

/* .news-toggle-button {
} */

.user-controls .logout-button {
  background-color: #fce0e0;
  color: #c0392b;
  border-color: #f5c6cb;
}

.user-controls .logout-button:hover {
  background-color: #f8c8c2;
  color: #a93226;
  border-color: #f1b0aa;
}

.controls-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px 10px;
  background-color: #f9f9f9;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.mode-button {
  padding: 10px 20px;
  border: 1px solid #007bff;
  border-radius: 6px;
  background-color: #ffffff;
  color: #007bff;
  cursor: pointer;
  font-size: 1em;
  font-weight: 500;
  transition: background-color 0.3s ease, color 0.3s ease;
}

.mode-button.active {
  background-color: #007bff;
  color: #ffffff;
}

.mode-button:hover:not(.active) {
  background-color: #e6f2ff;
}

.uploaders-container {
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: flex-start;
  padding: 10px 0;
  width: 100%;
  min-height: 100px;
  gap: 20px;
}

.uploader-component {
  flex: 1 1 0px;
  max-width: 450px;
  background-color: #fff;
  padding: 15px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.uploader-placeholder {
  flex: 1 1 0px;
  max-width: 450px;
}

.chart-container {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  padding: 0px;
  background-color: #ffffff;
  margin: 10px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.asset-timeframe-selector {
  position: absolute;
  top: 10px;
  left: 10px;
  background-color: rgba(240, 240, 240, 0.85);
  padding: 8px 12px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 10;
  display: flex;
  gap: 15px;
}

.selector-item {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  font-size: 14px;
  color: #333;
  cursor: default;
}

::v-deep .trading-vue {
  flex-grow: 1;
  min-height: 0;
}

.chart-status-indicators {
  padding: 5px 10px;
  text-align: center;
  font-size: 0.9em;
  width: 100%;
  box-sizing: border-box;
}

.status-message {
  padding: 8px;
  margin: 5px auto;
  border-radius: 4px;
  max-width: 80%;
  display: inline-block;
}

.loading-message {
  background-color: #e0e0e0;
  color: #333;
}

.backfill-message {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeeba;
}

/* Styles for the new Log in button */
.user-controls .login-button {
  background-color: #007bff; /* Primary blue */
  color: #ffffff;
  border-color: #007bff;
  text-decoration: none; /* Remove underline from router-link */
  display: inline-flex; /* Align text properly if needed */
  align-items: center; /* Align text properly if needed */
  justify-content: center; /* Align text properly if needed */
}

.user-controls .login-button:hover {
  background-color: #0056b3; /* Darker blue on hover */
  border-color: #0056b3;
  color: #ffffff;
}
</style>
