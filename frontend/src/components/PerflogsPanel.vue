<template>
  <div v-if="show" class="perflogs-panel">
    <div class="panel-header">
      <h3>
        Perflogs: {{ assetTicker || "N/A" }}
        <span v-if="assetTimeframe">({{ assetTimeframe }})</span>
      </h3>
      <button @click="closePanel" class="close-button-styled">
        <i class="fas fa-times"></i>
      </button>
    </div>

    <div class="panel-summary">
      <div class="summary-item">
        <strong>Total P&L:</strong>
        <span
          :class="{
            'positive-pnl': totalPnl >= 0,
            'negative-pnl': totalPnl < 0,
          }"
        >
          {{ formattedTotalPnl }}
        </span>
      </div>
      <div class="summary-item">
        <strong>Date Range:</strong> {{ dateRange.from }} - {{ dateRange.to }}
      </div>
    </div>

    <div class="panel-actions">
      <button
        v-if="!showAddNoteForm"
        @click="toggleAddNoteForm(true)"
        class="add-note-button-styled"
        :disabled="!assetTicker || assetTicker === 'N/A' || isLoading"
      >
        <i class="fas fa-plus"></i> Add Note for
        {{ assetTickerDisplay || "..." }}
      </button>
      <add-trade-note-form
        v-if="showAddNoteForm"
        :asset-ticker-prop="assetTicker"
        :asset-timeframe-prop="assetTimeframe"
        @note-saved="handleAddNoteSuccess"
        @cancel-add-note="toggleAddNoteForm(false)"
      />
    </div>

    <div v-if="isLoading" class="loading-indicator">
      <p><i class="fas fa-spinner fa-spin"></i> Loading trade notes...</p>
    </div>
    <div v-if="error" class="error-message">
      <p>{{ error }}</p>
    </div>

    <div class="trade-notes-list">
      <div v-if="!isLoading && tradeNotes.length === 0 && !error">
        <p class="no-notes-message">
          No trade notes recorded for this asset yet.
        </p>
      </div>
      <trade-note-card v-for="note in tradeNotes" :key="note.id" :note="note" />
    </div>
  </div>
</template>

<script>
import { mapState, mapActions, mapGetters } from "vuex";
import TradeNoteCard from "./TradeNoteCard.vue"; // Import the card component
import AddTradeNoteForm from "./AddTradeNoteForm.vue"; // Import the form component

export default {
  name: "PerflogsPanel",
  components: {
    TradeNoteCard, // Register the card component
    AddTradeNoteForm, // Register the form component
  },
  props: {
    show: {
      type: Boolean,
      required: true,
    },
    assetTicker: {
      type: String,
      default: null,
    },
    assetTimeframe: {
      type: String,
      default: null,
    },
  },
  data() {
    return {
      showAddNoteForm: false,
    };
  },
  computed: {
    ...mapState("perflogs", ["isLoading", "error"]),
    ...mapGetters("perflogs", [
      "getTradeNotesSorted",
      "getTotalPnl",
      "getDateRange",
    ]),
    tradeNotes() {
      return this.getTradeNotesSorted;
    },
    totalPnl() {
      return this.getTotalPnl;
    },
    dateRange() {
      return this.getDateRange;
    },
    assetTickerDisplay() {
      return this.assetTicker;
    },
    formattedTotalPnl() {
      const pnlValue = parseFloat(this.totalPnl);
      if (isNaN(pnlValue)) {
        return "N/A USD";
      }
      if (pnlValue === 0) {
        return "0.00 USD"; // Neutral color will be handled by lack of specific PNL class
      }
      const sign = pnlValue > 0 ? "+" : ""; // pnlValue < 0 will have '-' automatically
      return `${sign}${pnlValue.toFixed(2)} USD`;
    },
  },
  watch: {
    show(newVal) {
      if (newVal && this.assetTicker && this.assetTicker !== "N/A") {
        this.$store.dispatch("perflogs/setCurrentAssetContext", {
          assetTicker: this.assetTicker,
          timeframe: this.assetTimeframe,
        });
        this.fetchTradeNotes(this.assetTicker);
      } else if (!newVal) {
        this.clearPerflogsData();
        this.showAddNoteForm = false;
      } else if (newVal && (!this.assetTicker || this.assetTicker === "N/A")) {
        this.clearPerflogsData();
        this.showAddNoteForm = false;
        console.warn(
          "[PerflogsPanel] Panel shown but assetTicker is not valid:",
          this.assetTicker
        );
      }
    },
    assetTicker(newTicker, oldTicker) {
      if (this.show && newTicker !== oldTicker) {
        this.clearPerflogsData();
        this.showAddNoteForm = false;
        if (newTicker && newTicker !== "N/A") {
          this.$store.dispatch("perflogs/setCurrentAssetContext", {
            assetTicker: newTicker,
            timeframe: this.assetTimeframe,
          });
          this.fetchTradeNotes(newTicker);
        } else {
          this.$store.dispatch("perflogs/setCurrentAssetContext", {
            assetTicker: null,
            timeframe: null,
          });
        }
      }
    },
  },
  methods: {
    ...mapActions("perflogs", ["fetchTradeNotes", "clearPerflogsData"]),
    closePanel() {
      this.$emit("close-panel");
    },
    toggleAddNoteForm(show) {
      console.log(
        "[PerflogsPanel] toggleAddNoteForm called. Show:",
        show,
        "| Current assetTicker prop:",
        this.assetTicker,
        "| isLoading state:",
        this.isLoading,
        "| current showAddNoteForm:",
        this.showAddNoteForm
      );
      this.showAddNoteForm = show;
      if (show && !this.assetTicker) {
        alert(
          "Please ensure an asset is selected on the chart to add a perflog note."
        );
        this.showAddNoteForm = false;
      }
    },
    handleAddNoteSuccess() {
      this.showAddNoteForm = false;
      // Optionally, show a success notification here
      // Notes will be re-fetched by the watcher if needed or can be manually triggered
      // this.fetchTradeNotes(); // Or rely on currentAssetTicker watcher
    },
  },
  mounted() {
    if (this.show && this.assetTicker && this.assetTicker !== "N/A") {
      this.$store.dispatch("perflogs/setCurrentAssetContext", {
        assetTicker: this.assetTicker,
        timeframe: this.assetTimeframe,
      });
      this.fetchTradeNotes(this.assetTicker);
    } else if (this.show) {
      this.clearPerflogsData();
      this.showAddNoteForm = false;
      console.warn(
        "[PerflogsPanel] Mounted but assetTicker is not valid:",
        this.assetTicker
      );
    }
  },
};
</script>

<style scoped>
.perflogs-panel {
  position: fixed;
  right: 0;
  top: 0;
  width: 400px;
  height: 100vh;
  background-color: #2f3136;
  border-left: 1px solid #4f545c;
  box-shadow: -3px 0 10px rgba(0, 0, 0, 0.5);
  color: #dcddde;
  padding: 15px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  z-index: 1001;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background-color: #202225;
  border-bottom: 1px solid #2c2e33;
  border-radius: 8px 8px 0px 0px;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1em;
  color: #ffffff;
}

.close-button-styled {
  background: none;
  border: none;
  color: #dcddde;
  font-size: 1.5em;
  cursor: pointer;
  padding: 5px;
  line-height: 1;
}

.close-button-styled:hover {
  color: #ffffff;
}

.panel-summary {
  padding: 15px;
  background-color: #36393f;
  /* border: 1px solid #4f545c; */
  border-radius: 0px 0px 8px 8px;
  margin-bottom: 15px;
  box-sizing: border-box;
  width: 100%;
}

.summary-item {
  margin-bottom: 8px;
  font-size: 0.95em;
}

.summary-item:last-child {
  margin-bottom: 0;
}

.summary-item strong {
  color: #8e9297;
  margin-right: 5px;
}

.positive-pnl {
  color: #4caf50;
  font-weight: bold;
}

.negative-pnl {
  color: #f44336;
  font-weight: bold;
}

.panel-actions {
  padding: 0;
  margin-bottom: 15px;
  box-sizing: border-box;
  width: 100%;
}

.add-note-button-styled {
  background-color: #4a4d52;
  color: #ffffff;
  border: 1px solid #4f545c;
  padding: 12px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1em;
  width: 100%;
  text-align: center;
  transition: background-color 0.2s ease;
  box-sizing: border-box;
}

.add-note-button-styled:hover:not(:disabled) {
  background-color: #585b60;
}

.add-note-button-styled:disabled {
  background-color: #3a3c40;
  color: #72767d;
  cursor: not-allowed;
}

.loading-indicator,
.error-message {
  padding: 15px;
  text-align: center;
}

.trade-notes-list {
  padding: 0;
  overflow-y: auto;
  width: 100%;
  box-sizing: border-box;
}

/* Scrollbar styling for webkit browsers */
.trade-notes-list::-webkit-scrollbar {
  width: 8px;
}

.trade-notes-list::-webkit-scrollbar-track {
  background: #2f3136;
}

.trade-notes-list::-webkit-scrollbar-thumb {
  background-color: #4f545c;
  border-radius: 4px;
}

.trade-notes-list::-webkit-scrollbar-thumb:hover {
  background-color: #5c6168;
}

/*
.no-notes-message {
  background-color: #fff3cd; 
  color: #856404; 
  border: 1px solid #ffeeba; 
  border-left-width: 5px;
  border-left-color: #ffc107; 
  padding: 10px 15px;
  border-radius: 4px;
  margin: 15px 0;
  text-align: center;
  font-size: 0.9em;
}
*/

.no-notes-message {
  background-color: #ffc10720; /* Light orange/yellow background */
  color: #ffc107; /* Darker text color for contrast  a37f10 */
  border: 0px solid #ffeeba; /* Border color */
  border-left-width: 5px;
  border-left-color: #ffc107; /* Orange left border */
  padding: 10px 15px;
  border-radius: 4px;
  margin: 15px 0;
  text-align: center;
  font-size: 0.9em;
}
</style>
