import SampleData from "@/assets/data.json";
import DataCube from "@/trading-vue-core/helpers/datacube.js";

const getDefaultChartDataCube = () => {
  return new DataCube({
    chart: { type: "Candles", data: SampleData.chart.data },
    onchart: SampleData.onchart || [],
    offchart: SampleData.offchart || [],
  });
};

const getEmptyChartDataCube = () => {
  return new DataCube({
    chart: { type: "Candles", data: [] },
    onchart: [],
    offchart: [],
  });
};

const state = {
  customChartDataCube: getDefaultChartDataCube(), // For custom mode
  liveChartDataCube: getEmptyChartDataCube(), // For live mode
  chartMode: "custom", // Start in custom mode
  lastLiveAsset: "BTCUSDT",
  lastLiveTimeframe: "1m",
  currentDisplayAsset: "BTCUSDT", // New state for currently selected asset in UI
  currentDisplayTimeframeUserSelected: "1m", // New state for currently selected timeframe in UI
};

const mutations = {
  SET_CHART_DATA(state, newOhlcvArray) {
    state.customChartDataCube = new DataCube({
      chart: { type: "Candles", data: newOhlcvArray },
      onchart: [], // Reset overlays for customChartDataCube on new OHLCV
      offchart: [],
    });
    state.customChartDataCube._debug_id = "custom_ohlcv_" + Math.random();
  },
  ADD_SIGNALS(state, newSignalsArray) {
    const targetDataCube =
      state.chartMode === "live"
        ? state.liveChartDataCube
        : state.customChartDataCube;

    if (!targetDataCube) {
      console.error(
        "[chart.js] ADD_SIGNALS: Target DataCube is not initialized for mode:",
        state.chartMode
      );
      // Initialize if null, though this state should ideally be pre-initialized
      if (state.chartMode === "live") {
        state.liveChartDataCube = getEmptyChartDataCube();
        // Re-assign targetDataCube if it was created
        // This logic path indicates an unexpected state, ideally liveChartDataCube & customChartDataCube are always objects.
      } else {
        state.customChartDataCube = getDefaultChartDataCube();
      }
      // Consider if we need to re-assign targetDataCube here or if the mutation should fail/warn more strongly
      return; // Early exit if targetDataCube was null and had to be initialized, as it might not be reactive yet for .data
    }

    if (!targetDataCube.data) {
      targetDataCube.data = { onchart: [], offchart: [], chart: { data: [] } };
    }
    if (!Array.isArray(targetDataCube.data.onchart)) {
      targetDataCube.data.onchart = [];
    }
    targetDataCube.data.onchart = [
      ...targetDataCube.data.onchart,
      ...newSignalsArray,
    ];
    targetDataCube._debug_id = "signals_added_" + Math.random();
  },
  SET_CHART_MODE(state, mode) {
    if (["custom", "live"].includes(mode)) {
      state.chartMode = mode;
    } else {
      console.warn(`[chart.js] SET_CHART_MODE: Invalid mode '${mode}'`);
    }
  },
  SET_LAST_LIVE_ASSET(state, asset) {
    state.lastLiveAsset = asset;
  },
  SET_LAST_LIVE_TIMEFRAME(state, timeframe) {
    state.lastLiveTimeframe = timeframe;
  },
  RESET_CHART_TO_DEFAULT(state) {
    state.customChartDataCube = getDefaultChartDataCube();
    state.customChartDataCube._debug_id = "custom_reset_" + Math.random();
  },
  CLEAR_CHART_DATA(state) {
    state.liveChartDataCube = getEmptyChartDataCube();
    state.liveChartDataCube._debug_id = "live_clear_" + Math.random();
  },
  SET_LIVE_CHART_DATA(state, klinesArray) {
    let existingOnchart = [];
    let existingOffchart = [];
    if (state.liveChartDataCube && state.liveChartDataCube.data) {
      if (Array.isArray(state.liveChartDataCube.data.onchart)) {
        existingOnchart = state.liveChartDataCube.data.onchart;
      }
      if (Array.isArray(state.liveChartDataCube.data.offchart)) {
        existingOffchart = state.liveChartDataCube.data.offchart;
      }
    }
    state.liveChartDataCube = new DataCube({
      chart: { type: "Candles", data: klinesArray },
      onchart: existingOnchart,
      offchart: existingOffchart,
    });
    state.liveChartDataCube._debug_id = "live_data_set_" + Math.random();
  },
  PREPEND_HISTORICAL_KLINES(state, olderKlinesArray) {
    let currentKlines = [];
    let preservedOnchart = [];
    let preservedOffchart = [];

    if (state.liveChartDataCube) {
      // Try to get current klines from our canonical path first
      if (
        state.liveChartDataCube.data &&
        state.liveChartDataCube.data.chart &&
        Array.isArray(state.liveChartDataCube.data.chart.data) &&
        state.liveChartDataCube.data.chart.data.length > 0
      ) {
        currentKlines = state.liveChartDataCube.data.chart.data;
      }
      // Fallback: if trading-vue moved it to .ohlcv and cleared our canonical path
      else if (
        Array.isArray(state.liveChartDataCube.ohlcv) &&
        state.liveChartDataCube.ohlcv.length > 0
      ) {
        console.warn(
          "[chart.js] PREPEND_HISTORICAL_KLINES: Using .ohlcv as fallback for current klines."
        );
        currentKlines = state.liveChartDataCube.ohlcv;
      }

      // Preserve overlays from .data (canonical)
      if (state.liveChartDataCube.data) {
        if (Array.isArray(state.liveChartDataCube.data.onchart)) {
          preservedOnchart = state.liveChartDataCube.data.onchart;
        }
        if (Array.isArray(state.liveChartDataCube.data.offchart)) {
          preservedOffchart = state.liveChartDataCube.data.offchart;
        }
      }
      // If overlays are not in .data, but perhaps on root (if trading-vue also moved them - less likely but defensive)
      // This part is more speculative, as onchart/offchart are usually less problematic.
      else {
        if (Array.isArray(state.liveChartDataCube.onchart)) {
          console.warn(
            "[chart.js] PREPEND_HISTORICAL_KLINES: Using root .onchart as fallback for preserved overlays."
          );
          preservedOnchart = state.liveChartDataCube.onchart;
        }
        if (Array.isArray(state.liveChartDataCube.offchart)) {
          console.warn(
            "[chart.js] PREPEND_HISTORICAL_KLINES: Using root .offchart as fallback for preserved overlays."
          );
          preservedOffchart = state.liveChartDataCube.offchart;
        }
      }
    } else {
      // This case should ideally not be hit if liveChartDataCube is always initialized
      console.error(
        "[chart.js] PREPEND_HISTORICAL_KLINES: liveChartDataCube is not initialized."
      );
      // Initialize with only the new klines if the main object is missing
      state.liveChartDataCube = new DataCube({
        chart: { type: "Candles", data: olderKlinesArray },
        onchart: [],
        offchart: [],
      });
      state.liveChartDataCube._debug_id =
        "live_prep_fresh_init_" + Math.random();
      return; // Exit after fresh initialization
    }

    const combinedKlines = [...olderKlinesArray, ...currentKlines];
    combinedKlines.sort((a, b) => a[0] - b[0]);
    const uniqueKlines = [];
    const seenTimestamps = new Set();
    for (const kline of combinedKlines) {
      if (!seenTimestamps.has(kline[0])) {
        uniqueKlines.push(kline);
        seenTimestamps.add(kline[0]);
      }
    }

    state.liveChartDataCube = new DataCube({
      chart: { type: "Candles", data: uniqueKlines },
      onchart: preservedOnchart,
      offchart: preservedOffchart,
    });
    state.liveChartDataCube._debug_id = "live_prepended_" + Math.random();
  },
  UPDATE_LIVE_KLINE(state, newKline) {
    const currentLiveCube = state.liveChartDataCube;
    let klines = [];
    let preservedOnchart = [];
    let preservedOffchart = [];

    if (currentLiveCube) {
      // Try to get klines from the canonical path first
      if (
        currentLiveCube.data &&
        currentLiveCube.data.chart &&
        Array.isArray(currentLiveCube.data.chart.data)
      ) {
        klines = [...currentLiveCube.data.chart.data]; // Operate on a copy
      }
      // Fallback to .ohlcv if canonical path is not a valid array (e.g., trading-vue moved it)
      else if (Array.isArray(currentLiveCube.ohlcv)) {
        console.warn(
          "[chart.js] UPDATE_LIVE_KLINE: Using .ohlcv as fallback for current klines."
        );
        klines = [...currentLiveCube.ohlcv]; // Operate on a copy
      }
      // If neither path yields klines, it will remain an empty array, and the newKline will be the first.

      // Preserve overlays - robust check from .data or root
      if (currentLiveCube.data) {
        if (Array.isArray(currentLiveCube.data.onchart))
          preservedOnchart = currentLiveCube.data.onchart;
        if (Array.isArray(currentLiveCube.data.offchart))
          preservedOffchart = currentLiveCube.data.offchart;
      } else {
        // Fallback to root overlays if .data is not present
        if (Array.isArray(currentLiveCube.onchart))
          preservedOnchart = currentLiveCube.onchart;
        if (Array.isArray(currentLiveCube.offchart))
          preservedOffchart = currentLiveCube.offchart;
        if (currentLiveCube.onchart || currentLiveCube.offchart) {
          console.warn(
            "[chart.js] UPDATE_LIVE_KLINE: Using root overlays as fallback."
          );
        }
      }
    } else {
      console.error(
        "[chart.js] UPDATE_LIVE_KLINE: state.liveChartDataCube is null. This should not happen."
      );
      // Initialize with only the new kline if the main object is somehow missing
      state.liveChartDataCube = new DataCube({
        chart: { type: "Candles", data: [newKline] },
        onchart: [],
        offchart: [],
      });
      state.liveChartDataCube._debug_id =
        "live_update_emergency_init_" + Math.random();
      return;
    }

    // Perform kline update logic on the 'klines' array
    const lastKline = klines.length > 0 ? klines[klines.length - 1] : null;

    if (lastKline && lastKline[0] === newKline[0]) {
      // Existing kline updated
      klines.splice(klines.length - 1, 1, newKline);
    } else if (!lastKline || newKline[0] > lastKline[0]) {
      // New kline appended
      klines.push(newKline);
    } else {
      // Out-of-order kline, insert it correctly
      console.warn(
        "[chart.js] UPDATE_LIVE_KLINE: Received kline older than last. Inserting in order."
      );
      let inserted = false;
      for (let i = klines.length - 1; i >= 0; i--) {
        if (newKline[0] > klines[i][0]) {
          klines.splice(i + 1, 0, newKline);
          inserted = true;
          break;
        } else if (newKline[0] === klines[i][0]) {
          // Should have been caught by the first 'if', but for safety
          klines.splice(i, 1, newKline);
          inserted = true;
          break;
        }
      }
      if (!inserted) {
        klines.unshift(newKline); // If it's the new oldest
      }
    }

    // ALWAYS create a new DataCube instance with the full, updated kline list
    state.liveChartDataCube = new DataCube({
      chart: { type: "Candles", data: klines },
      onchart: preservedOnchart,
      offchart: preservedOffchart,
    });
    state.liveChartDataCube._debug_id = "live_updated_kline_" + Math.random();
  },
  CLEAR_CHART_DATA_FOR_NEW_CONTEXT(state) {
    // For asset/timeframe change, clear OHLCV and overlays for both modes.
    state.liveChartDataCube = getEmptyChartDataCube();
    state.liveChartDataCube._debug_id = "live_ctx_reset_" + Math.random();
    state.customChartDataCube = getEmptyChartDataCube();
    state.customChartDataCube._debug_id = "custom_ctx_reset_" + Math.random();
    console.log(
      "[chart.js] Chart data and overlays cleared for new context in both modes."
    );
  },
  SET_CURRENT_DISPLAY_ASSET(state, asset) {
    state.currentDisplayAsset = asset;
  },
  SET_CURRENT_DISPLAY_TIMEFRAME_USER_SELECTED(state, timeframe) {
    state.currentDisplayTimeframeUserSelected = timeframe;
  },
  PROCESS_LIVE_KLINE_TICK(state, tickData) {
    const currentLiveCube = state.liveChartDataCube;
    if (!currentLiveCube) {
      console.error(
        "[chart.js] PROCESS_LIVE_KLINE_TICK: liveChartDataCube is not initialized."
      );
      return;
    }

    let klines = [];
    if (
      currentLiveCube.data &&
      currentLiveCube.data.chart &&
      Array.isArray(currentLiveCube.data.chart.data)
    ) {
      klines = currentLiveCube.data.chart.data;
    } else if (Array.isArray(currentLiveCube.ohlcv)) {
      console.warn(
        "[chart.js] PROCESS_LIVE_KLINE_TICK: Using .ohlcv as fallback for current klines array."
      );
      klines = currentLiveCube.ohlcv;
    } else {
      console.error(
        "[chart.js] PROCESS_LIVE_KLINE_TICK: Could not find klines array in liveChartDataCube."
      );
      klines = [];
    }

    const newTickKline = [
      parseInt(tickData.open_time, 10),
      parseFloat(tickData.open),
      parseFloat(tickData.high),
      parseFloat(tickData.low),
      parseFloat(tickData.close),
      parseFloat(tickData.volume),
    ];

    if (klines.length > 0) {
      const lastKline = klines[klines.length - 1];
      const lastKlineOpenTime = lastKline[0];

      if (newTickKline[0] === lastKlineOpenTime) {
        lastKline[2] = Math.max(lastKline[2], newTickKline[2]); // High
        lastKline[3] = Math.min(lastKline[3], newTickKline[3]); // Low
        lastKline[4] = newTickKline[4]; // Close
        lastKline[5] = newTickKline[5]; // Volume
      } else if (newTickKline[0] > lastKlineOpenTime) {
        klines.push(newTickKline);
      } else {
        console.warn(
          "[chart.js] PROCESS_LIVE_KLINE_TICK: Received tick older than last kline or with unhandled open_time. Tick OT:",
          newTickKline[0],
          "Last Kline OT:",
          lastKlineOpenTime
        );
        return;
      }
    } else {
      klines.push(newTickKline);
    }

    let existingOnchart = [];
    let existingOffchart = [];
    if (currentLiveCube.data) {
      if (Array.isArray(currentLiveCube.data.onchart)) {
        existingOnchart = currentLiveCube.data.onchart;
      }
      if (Array.isArray(currentLiveCube.data.offchart)) {
        existingOffchart = currentLiveCube.data.offchart;
      }
    } else if (currentLiveCube.onchart || currentLiveCube.offchart) {
      existingOnchart = Array.isArray(currentLiveCube.onchart)
        ? currentLiveCube.onchart
        : [];
      existingOffchart = Array.isArray(currentLiveCube.offchart)
        ? currentLiveCube.offchart
        : [];
    }

    state.liveChartDataCube = new DataCube({
      chart: { type: "Candles", data: [...klines] },
      onchart: existingOnchart,
      offchart: existingOffchart,
    });
    state.liveChartDataCube._debug_id = "live_tick_processed_" + Math.random();
  },
};

const actions = {
  loadInitialChartData({ commit, state }) {
    // This action is called on app mount.
    // Initializes customChartDataCube if it wasn't (though it is by default state).
    // For live mode, Home.vue will trigger initial data load based on watching chartMode.
    if (!state.customChartDataCube) {
      // Should always be true due to initial state
      commit("RESET_CHART_TO_DEFAULT");
    }
    if (!state.liveChartDataCube) {
      // Should always be true
      commit("CLEAR_CHART_DATA");
    }
  },
  setUploadedChartData({ commit }, uploadedDataArray) {
    commit("SET_CHART_DATA", uploadedDataArray);
  },
  addSignalOverlays({ commit }, signalsArray) {
    if (signalsArray && signalsArray.length > 0) {
      commit("ADD_SIGNALS", signalsArray);
    } else {
      console.warn("[chart.js] addSignalOverlays: No signals provided to add.");
    }
  },
  setChartMode({ commit, state }, mode) {
    if (state.chartMode === mode) return; // No change
    commit("SET_CHART_MODE", mode);
    // Actions below are more about setup when mode becomes active FIRST time or asset changes.
    // Actual data loading logic might be better handled in Home.vue's watcher for chartMode.
    // if (mode === "custom") {
    // dispatch("switchToCustomModeAction"); // Not strictly needed if customChartDataCube is preserved
    // } else if (mode === "live") {
    // dispatch("switchToLiveModeAction"); // Home.vue will handle fetching
    // }
  },
  // switchToCustomModeAction({ commit }) { // Potentially remove if not doing more than setting mode
  // commit("RESET_CHART_TO_DEFAULT"); // Only if we want to always reset custom on switch
  // },
  // switchToLiveModeAction({ commit, state }) { // Potentially remove
  // commit("CLEAR_CHART_DATA"); // Only if we want to always clear live on switch
  // Home.vue will fetch initial data if liveChartDataCube.data.chart.data is empty for current asset/tf
  // },
  setLastLiveAssetAndTimeframe({ commit, state }, { asset, timeframe }) {
    if (asset && state.lastLiveAsset !== asset) {
      commit("SET_LAST_LIVE_ASSET", asset);
    }
    if (timeframe && state.lastLiveTimeframe !== timeframe) {
      commit("SET_LAST_LIVE_TIMEFRAME", timeframe);
    }
    // REMOVED: Data clearing logic is now handled by resetChartForNewContext in Home.vue's context change handler
    // if (changed && state.chartMode === 'live') {
    //   commit("CLEAR_CHART_DATA");
    // }
  },
  setLiveChartData({ commit }, klinesArray) {
    commit("SET_LIVE_CHART_DATA", klinesArray);
  },
  async prependHistoricalKlines({ commit }, olderKlinesArray) {
    if (!olderKlinesArray || olderKlinesArray.length === 0) {
      return; // Action simply returns if no data to prepend
    }
    commit("PREPEND_HISTORICAL_KLINES", olderKlinesArray);
    // The actual new oldest timestamp is now handled by the calling component
    // based on the data it fetched.
  },
  updateLiveKline({ commit }, newKlineMessage) {
    try {
      const klineData =
        typeof newKlineMessage === "string"
          ? JSON.parse(newKlineMessage)
          : newKlineMessage;
      if (Array.isArray(klineData) && klineData.length >= 6) {
        commit("UPDATE_LIVE_KLINE", klineData);
      } else {
        console.error(
          "[chart.js] updateLiveKline: Invalid kline data received",
          klineData
        );
      }
    } catch (error) {
      console.error(
        "[chart.js] updateLiveKline: Error processing WebSocket message",
        error,
        newKlineMessage
      );
    }
  },
  updateCurrentDisplayAsset({ commit, dispatch, state }, asset) {
    commit("SET_CURRENT_DISPLAY_ASSET", asset);
    if (state.chartMode === "live") {
      // Keep lastLiveAsset in sync if we are in live mode
      dispatch("setLastLiveAssetAndTimeframe", {
        asset,
        timeframe: state.currentDisplayTimeframeUserSelected,
      });
    }
  },
  updateCurrentDisplayTimeframeUserSelected(
    { commit, dispatch, state },
    timeframe
  ) {
    commit("SET_CURRENT_DISPLAY_TIMEFRAME_USER_SELECTED", timeframe);
    if (state.chartMode === "live") {
      // Keep lastLiveTimeframe in sync if we are in live mode
      dispatch("setLastLiveAssetAndTimeframe", {
        asset: state.currentDisplayAsset,
        timeframe,
      });
    }
  },
  resetChartForNewContext({ commit }) {
    commit("CLEAR_CHART_DATA_FOR_NEW_CONTEXT");
    // commit("RESET_CHART_TO_DEFAULT");
  },
  processLiveKlineTick({ commit }, tickData) {
    commit("PROCESS_LIVE_KLINE_TICK", tickData);
  },
};

const getters = {
  getChartDataCube: (state) => {
    if (state.chartMode === "live") {
      return state.liveChartDataCube;
    }
    return state.customChartDataCube;
  },
  getChartMode: (state) => state.chartMode,
  getLastLiveAsset: (state) => state.lastLiveAsset,
  getLastLiveTimeframe: (state) => state.lastLiveTimeframe,
  getCurrentDisplayAsset: (state) => state.currentDisplayAsset,
  getCurrentDisplayTimeframeUserSelected: (state) =>
    state.currentDisplayTimeframeUserSelected,
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters,
};
