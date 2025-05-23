import axios from "axios";

const state = {
  tradeNotes: [],
  isLoading: false,
  error: null,
  currentAssetTicker: null,
  currentAssetTimeframe: null,
};

const mutations = {
  SET_TRADE_NOTES(state, notes) {
    state.tradeNotes = notes;
  },
  ADD_TRADE_NOTE(state, note) {
    state.tradeNotes.unshift(note); // Add to the beginning for chronological display
  },
  REMOVE_TRADE_NOTE(state, noteId) {
    state.tradeNotes = state.tradeNotes.filter((note) => note.id !== noteId);
  },
  SET_LOADING(state, isLoading) {
    state.isLoading = isLoading;
  },
  SET_ERROR(state, error) {
    state.error = error;
  },
  CLEAR_PERFLOGS_DATA(state) {
    state.tradeNotes = [];
    state.isLoading = false;
    state.error = null;
    // currentAssetTicker and currentAssetTimeframe are intentionally not cleared here
    // as they might be needed to re-fetch data if the panel is reopened for the same asset.
  },
  SET_CURRENT_ASSET_CONTEXT(state, { ticker, timeframe }) {
    state.currentAssetTicker = ticker;
    state.currentAssetTimeframe = timeframe;
  },
};

const actions = {
  async fetchTradeNotes(
    { commit, state, rootState },
    assetTickerPayload = null
  ) {
    const tickerToFetch = assetTickerPayload || state.currentAssetTicker;

    if (!tickerToFetch) {
      commit("SET_ERROR", "No asset selected to fetch trade notes.");
      return;
    }
    commit("SET_LOADING", true);
    commit("SET_ERROR", null);
    try {
      const token = rootState.auth.token;
      const response = await axios.get(
        `http://localhost:8000/api/perflogs/notes/${tickerToFetch}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      commit("SET_TRADE_NOTES", response.data);
    } catch (error) {
      console.error(
        "Error fetching trade notes:",
        error.response?.data || error.message
      );
      commit(
        "SET_ERROR",
        error.response?.data?.detail || "Failed to fetch trade notes."
      );
    } finally {
      commit("SET_LOADING", false);
    }
  },

  async submitTradeNote({ commit, rootState }, tradeNoteData) {
    commit("SET_LOADING", true);
    commit("SET_ERROR", null);
    try {
      const token = rootState.auth.token;
      const payload = { ...tradeNoteData };

      const response = await axios.post(
        "http://localhost:8000/api/perflogs/notes/",
        payload,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      commit("ADD_TRADE_NOTE", response.data);
      return response.data; // Return created note
    } catch (error) {
      console.error(
        "Error submitting trade note:",
        error.response?.data || error.message
      );
      commit(
        "SET_ERROR",
        error.response?.data?.detail || "Failed to submit trade note."
      );
      throw error; // Re-throw to allow form to handle it
    } finally {
      commit("SET_LOADING", false);
    }
  },

  async deleteTradeNote({ commit, rootState }, noteId) {
    commit("SET_LOADING", true); // Optional: depends on UX for individual deletions
    commit("SET_ERROR", null);
    try {
      const token = rootState.auth.token;
      await axios.delete(`http://localhost:8000/api/perflogs/notes/${noteId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      commit("REMOVE_TRADE_NOTE", noteId);
    } catch (error) {
      console.error(
        "Error deleting trade note:",
        error.response?.data || error.message
      );
      commit(
        "SET_ERROR",
        error.response?.data?.detail || "Failed to delete trade note."
      );
    } finally {
      commit("SET_LOADING", false); // Optional
    }
  },

  clearPerflogsData({ commit }) {
    commit("CLEAR_PERFLOGS_DATA");
  },

  setCurrentAssetContext({ commit }, { ticker, timeframe }) {
    commit("SET_CURRENT_ASSET_CONTEXT", { ticker, timeframe });
    // No longer immediately fetching here, PerflogsPanel controls fetching
  },
};

const getters = {
  getTradeNotesSorted: (state) => {
    // Notes are added to the beginning, so they are already reverse chronological by default
    return state.tradeNotes;
  },
  getTotalPnl: (state) => {
    return state.tradeNotes.reduce(
      (total, note) => total + parseFloat(note.pnl || 0),
      0
    );
  },
  getDateRange: (state) => {
    if (state.tradeNotes.length === 0) {
      return { from: null, to: null };
    }
    // Assuming notes are somewhat sorted or we just care about overall min/max
    const timestamps = state.tradeNotes.map((note) =>
      new Date(note.created_at).getTime()
    );
    const minTimestamp = Math.min(...timestamps);
    const maxTimestamp = Math.max(...timestamps);
    return {
      from: minTimestamp ? new Date(minTimestamp).toLocaleDateString() : null,
      to: maxTimestamp ? new Date(maxTimestamp).toLocaleDateString() : null,
    };
  },
  isLoadingPerflogs: (state) => state.isLoading,
  perflogsError: (state) => state.error,
  currentPerflogAsset: (state) => state.currentAssetTicker,
  currentPerflogTimeframe: (state) => state.currentAssetTimeframe,
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters,
};
