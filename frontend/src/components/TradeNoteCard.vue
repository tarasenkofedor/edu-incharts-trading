<template>
  <div class="trade-note-card">
    <div class="card-header">
      <span class="asset-ticker">{{ note.asset_ticker }}</span>
      <span class="timeframe">{{ note.timeframe }}</span>
      <span :class="['trade-direction', note.trade_direction.toLowerCase()]">
        {{ note.trade_direction }}
      </span>
      <button
        @click="handleDelete"
        class="delete-button-icon"
        title="Delete Note"
      >
        <i class="fas fa-trash-alt"></i>
      </button>
    </div>

    <div class="card-body">
      <div class="details-grid">
        <div class="detail-item">
          <strong>Entry:</strong> {{ formatPrice(note.entry_price) }}
        </div>
        <div class="detail-item">
          <strong>Exit:</strong> {{ formatPrice(note.exit_price) }}
        </div>
        <div class="detail-item">
          <strong>Margin:</strong> {{ formatPrice(note.margin) }}
        </div>
        <div class="detail-item">
          <strong>Leverage:</strong> {{ note.leverage }}x
        </div>
      </div>
      <div class="pnl-item">
        <strong>PnL:</strong>
        <span
          :class="{
            'positive-pnl': note.pnl >= 0,
            'negative-pnl': note.pnl < 0,
          }"
        >
          {{ formattedPnl }}
        </span>
      </div>
      <div v-if="note.note_text" class="note-text-section">
        <strong>Note:</strong>
        <p class="note-content" :class="{ expanded: isNoteExpanded }">
          {{ note.note_text }}
        </p>
        <button
          v-if="note.note_text.length > noteTextPreviewLength"
          @click="toggleNoteExpansion"
          class="read-more-button"
        >
          {{ isNoteExpanded ? "Read Less" : "Read More" }}
        </button>
      </div>
    </div>

    <div class="card-footer">
      <small>Created: {{ formatDate(note.created_at) }}</small>
      <small v-if="note.updated_at && note.updated_at !== note.created_at">
        Updated: {{ formatDate(note.updated_at) }}
      </small>
    </div>
  </div>
</template>

<script>
import { mapActions } from "vuex";

export default {
  name: "TradeNoteCard",
  props: {
    note: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      isNoteExpanded: false,
      noteTextPreviewLength: 100, // Max characters for preview
    };
  },
  computed: {
    formattedPnl() {
      const pnlValue = parseFloat(this.note.pnl);
      if (isNaN(pnlValue)) {
        return this.note.pnl || "N/A USD"; // Fallback for non-numeric or null pnl
      }
      const sign = pnlValue >= 0 ? "+" : "";
      return `${sign}${pnlValue.toFixed(2)} USD`; // Ensures XX.XX format and adds sign + USD
    },
  },
  methods: {
    ...mapActions("perflogs", ["deleteTradeNote"]),
    formatPrice(value) {
      const num = parseFloat(value);
      if (isNaN(num)) return value; // Return original if not a number
      // Adjust toFixed based on typical precision for your assets
      return num.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 8,
      });
    },
    formatDate(dateString) {
      if (!dateString) return "";
      const date = new Date(dateString);
      return date.toLocaleString(); // Or use a more specific format
    },
    async handleDelete() {
      if (confirm("Are you sure you want to delete this trade note?")) {
        try {
          await this.deleteTradeNote(this.note.id);
          // Optionally, show a success notification
        } catch (error) {
          // Error is handled in Vuex action, but can show a local notification too
          alert("Failed to delete note. Please try again.");
        }
      }
    },
    toggleNoteExpansion() {
      this.isNoteExpanded = !this.isNoteExpanded;
    },
  },
};
</script>

<style scoped>
.trade-note-card {
  background-color: #36393f;
  border: 1px solid #4f545c;
  border-radius: 8px;
  margin-bottom: 15px;
  padding: 15px;
  color: #dcddde; /* Light gray text */
  font-size: 0.9em;
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #4a4e54;
}

.asset-ticker {
  font-weight: bold;
  font-size: 1.2em;
  color: #ffffff;
  margin-right: 10px;
}

.timeframe {
  background-color: #4f545c;
  color: #b0b8c4;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8em;
  margin-right: 10px;
}

.trade-direction {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
  text-transform: uppercase;
}

.trade-direction.long {
  background-color: #4caf50; /* Green for long */
  color: #ffffff;
}

.trade-direction.short {
  background-color: #f44336; /* Red for short */
  color: #ffffff;
}

.delete-button-icon {
  margin-left: auto;
  background-color: transparent;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #dcddde;
  font-size: 1.1em;
  transition: background-color 0.2s ease, transform 0.1s ease;
}

.delete-button-icon i {
  color: #dcddde;
}

.delete-button-icon:hover i {
  color: #ffffff;
}

.delete-button-icon:hover {
  background-color: rgba(
    220,
    53,
    69,
    0.8
  ); /* More opaque red on hover for background */
  transform: scale(1.1);
}

.delete-button-icon:active {
  transform: scale(1.05); /* Slight press effect */
}

.card-body {
  margin-bottom: 10px;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.detail-item strong {
  color: #8e9297; /* Mid-gray for labels */
  margin-right: 5px;
}

.pnl-item strong {
  color: #8e9297;
}
.pnl-item span {
  font-weight: bold;
}

.positive-pnl {
  color: #4caf50;
}

.negative-pnl {
  color: #f44336;
}

.note-text-section {
  margin-top: 10px;
}
.note-text-section strong {
  color: #8e9297;
  display: block;
  margin-bottom: 4px;
}

.note-content {
  white-space: pre-wrap; /* Preserve line breaks and spaces */
  word-break: break-word;
  font-size: 0.95em;
  line-height: 1.5;
  max-height: 60px; /* Approx 3 lines for preview */
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.note-content.expanded {
  max-height: none;
  -webkit-line-clamp: unset;
}

.read-more-button {
  background: none;
  border: none;
  color: #7289da;
  cursor: pointer;
  font-size: 0.85em;
  padding: 4px 0;
  text-decoration: underline;
}
.read-more-button:hover {
  color: #99aab5;
}

.card-footer {
  font-size: 0.8em;
  color: #72767d; /* Darker gray for footer */
  text-align: right;
}
.card-footer small:not(:last-child)::after {
  content: " | ";
  margin: 0 5px;
}
</style>
