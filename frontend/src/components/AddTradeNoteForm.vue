<template>
  <div class="add-trade-note-form">
    <h4>Add New Trade Note</h4>
    <form @submit.prevent="handleSubmit">
      <div class="form-group asset-context">
        <p><strong>Asset:</strong> {{ assetTickerProp || "N/A" }}</p>
        <p><strong>Timeframe:</strong> {{ assetTimeframeProp || "N/A" }}</p>
      </div>

      <div class="form-group">
        <label for="trade-direction">Direction:</label>
        <select id="trade-direction" v-model="form.trade_direction" required>
          <option value="long">Long</option>
          <option value="short">Short</option>
        </select>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="entry-price">Entry Price:</label>
          <input
            type="number"
            id="entry-price"
            v-model.number="form.entry_price"
            step="any"
            required
            placeholder="0.00"
          />
        </div>
        <div class="form-group">
          <label for="exit-price">Exit Price:</label>
          <input
            type="number"
            id="exit-price"
            v-model.number="form.exit_price"
            step="any"
            required
            placeholder="0.00"
          />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="margin">Margin:</label>
          <input
            type="number"
            id="margin"
            v-model.number="form.margin"
            step="any"
            required
            placeholder="0.00"
          />
        </div>
        <div class="form-group">
          <label for="leverage">Leverage:</label>
          <input
            type="number"
            id="leverage"
            v-model.number="form.leverage"
            step="any"
            min="1"
            placeholder="1.0"
          />
        </div>
      </div>

      <div class="form-group calculated-pnl">
        <label>Calculated PnL:</label>
        <span
          :class="{
            'positive-pnl': calculatedPnl > 0,
            'negative-pnl': calculatedPnl < 0,
            'pnl-na': isNaN(calculatedPnl),
            'neutral-pnl': !isNaN(calculatedPnl) && calculatedPnl === 0,
          }"
        >
          {{ formattedCalculatedPnl }}
        </span>
      </div>

      <div class="form-group">
        <label for="note-text">Note (Optional):</label>
        <textarea
          id="note-text"
          v-model.trim="form.note_text"
          :maxlength="maxNoteLength"
          placeholder="Enter your trade analysis or remarks..."
        ></textarea>
        <small class="char-counter"
          >{{ form.note_text.length }} / {{ maxNoteLength }}</small
        >
        <small v-if="form.note_text.length > maxNoteLength" class="error-text"
          >Note exceeds maximum length.</small
        >
      </div>

      <div v-if="submissionError" class="error-message submit-error">
        <p>{{ submissionError }}</p>
      </div>

      <div class="form-actions">
        <button
          type="submit"
          :disabled="
            isSubmitting ||
            form.note_text.length > maxNoteLength ||
            !isFormValid
          "
        >
          {{ isSubmitting ? "Submitting..." : "Save Note" }}
        </button>
        <button type="button" @click="handleCancel" class="cancel-button">
          Cancel
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import { mapActions } from "vuex";

export default {
  name: "AddTradeNoteForm",
  props: {
    assetTickerProp: {
      type: String,
      required: true,
    },
    assetTimeframeProp: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      form: {
        trade_direction: "long",
        entry_price: null,
        exit_price: null,
        margin: null,
        leverage: 1.0,
        note_text: "",
        // pnl will be calculated
      },
      maxNoteLength: 1000,
      isSubmitting: false,
      submissionError: null,
    };
  },
  computed: {
    calculatedPnl() {
      const entry = parseFloat(this.form.entry_price);
      const exit = parseFloat(this.form.exit_price);
      const margin = parseFloat(this.form.margin);
      let leverage = parseFloat(this.form.leverage);

      if (
        isNaN(entry) ||
        isNaN(exit) ||
        isNaN(margin) ||
        entry <= 0 ||
        margin <= 0
      ) {
        return NaN;
      }
      if (isNaN(leverage) || leverage < 1) {
        leverage = 1.0;
      }

      let pnl = 0;
      if (this.form.trade_direction === "long") {
        pnl = (exit / entry - 1) * margin * leverage;
      } else if (this.form.trade_direction === "short") {
        pnl = (1 - exit / entry) * margin * leverage;
      }
      return pnl;
    },
    formattedCalculatedPnl() {
      if (isNaN(this.calculatedPnl)) {
        return "N/A";
      }
      const pnlValue = this.calculatedPnl;
      const sign = pnlValue > 0 ? "+" : "";
      return `${sign}${pnlValue.toFixed(2)} USD`;
    },
    isFormValid() {
      return (
        this.form.entry_price !== null &&
        this.form.entry_price > 0 &&
        this.form.exit_price !== null &&
        this.form.exit_price > 0 &&
        this.form.margin !== null &&
        this.form.margin > 0 &&
        (this.form.leverage === null ||
          (typeof this.form.leverage === "number" &&
            this.form.leverage >= 1)) &&
        this.form.note_text.length <= this.maxNoteLength &&
        !isNaN(this.calculatedPnl) // Ensure PnL is a valid number
      );
    },
  },
  methods: {
    ...mapActions("perflogs", ["submitTradeNote"]),
    async handleSubmit() {
      if (!this.isFormValid) {
        this.submissionError =
          "Please correct the form errors before submitting.";
        return;
      }
      if (
        !this.assetTickerProp ||
        !this.assetTimeframeProp ||
        this.assetTickerProp === "N/A"
      ) {
        this.submissionError =
          "Asset context is not properly set. Cannot save note.";
        return;
      }

      this.isSubmitting = true;
      this.submissionError = null;
      try {
        const payload = {
          ...this.form,
          pnl: this.calculatedPnl,
          asset_ticker: this.assetTickerProp,
          timeframe: this.assetTimeframeProp,
        };
        console.log(
          "[AddTradeNoteForm] Payload to be submitted:",
          JSON.stringify(payload, null, 2)
        );
        await this.submitTradeNote(payload);
        this.$emit("note-saved");
        this.resetForm();
      } catch (error) {
        this.submissionError =
          error.response?.data?.detail ||
          "An error occurred while saving the note.";
      } finally {
        this.isSubmitting = false;
      }
    },
    resetForm() {
      this.form = {
        trade_direction: "long",
        entry_price: null,
        exit_price: null,
        margin: null,
        leverage: 1.0,
        note_text: "",
      };
      this.submissionError = null;
    },
    handleCancel() {
      this.resetForm();
      this.$emit("cancel-add-note");
    },
  },
  watch: {
    assetTickerProp: {
      handler(newVal, oldVal) {
        if (newVal !== oldVal) {
          this.resetForm();
        }
      },
    },
    assetTimeframeProp: {
      handler(newVal, oldVal) {
        if (newVal !== oldVal) {
          this.resetForm();
        }
      },
    },
  },
};
</script>

<style scoped>
.add-trade-note-form {
  background-color: #3b3e45; /* Slightly different background for form area */
  padding: 20px;
  border-radius: 8px;
  margin-top: 15px;
  border: 1px solid #4f545c;
}

.add-trade-note-form h4 {
  margin-top: 0;
  margin-bottom: 20px;
  text-align: center;
  color: #ffffff;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #b0b8c4;
  font-size: 0.9em;
}

.form-group input[type="number"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  background-color: #2c2f33;
  border: 1px solid #4f545c;
  border-radius: 5px;
  color: #dcddde;
  box-sizing: border-box;
  font-size: 0.95em;
}

.form-group input[type="number"]:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #7289da;
  box-shadow: 0 0 0 2px rgba(114, 137, 218, 0.3);
}

.form-row {
  display: flex;
  gap: 15px;
}
.form-row .form-group {
  flex: 1;
}

.asset-context p {
  margin: 2px 0;
  font-size: 0.9em;
  color: #c0c2c5;
}
.asset-context p strong {
  color: #909399;
}

.calculated-pnl label {
  margin-right: 10px;
}
.calculated-pnl span {
  font-weight: bold;
  font-size: 1.1em;
}
.pnl-na {
  color: #909399; /* Grey for N/A PnL */
}
.positive-pnl {
  color: #4caf50;
}
.negative-pnl {
  color: #f44336;
}

.char-counter {
  display: block;
  text-align: right;
  font-size: 0.8em;
  color: #72767d;
  margin-top: 3px;
}

.error-text {
  display: block;
  color: #f44336;
  font-size: 0.8em;
  margin-top: 3px;
}

.submit-error p {
  background-color: rgba(244, 67, 54, 0.1);
  color: #f44336;
  padding: 10px;
  border-radius: 5px;
  font-size: 0.9em;
  border: 1px solid rgba(244, 67, 54, 0.3);
  text-align: center;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.form-actions button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.2s, opacity 0.2s;
}

.form-actions button[type="submit"] {
  background-color: #43b581; /* Green for save */
  color: white;
}
.form-actions button[type="submit"]:hover {
  background-color: #3aa070;
}
.form-actions button[type="submit"]:disabled {
  background-color: #3a4b53;
  opacity: 0.7;
  cursor: not-allowed;
}

.form-actions .cancel-button {
  background-color: #4f545c;
  color: #dcddde;
}
.form-actions .cancel-button:hover {
  background-color: #5c626d;
}
</style>
