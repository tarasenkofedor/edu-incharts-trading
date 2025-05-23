<template>
  <div class="asset-timeframe-selector-display">
    <span
      class="selector-item asset-item"
      @dblclick="editAsset"
      v-if="!isEditingAsset"
    >
      Asset: <strong>{{ asset || "N/A" }}</strong>
    </span>
    <input
      v-if="isEditingAsset"
      type="text"
      v-model="editableAsset"
      @keyup.enter="saveAsset"
      @blur="saveAsset"
      ref="assetInput"
      class="asset-input"
    />
    <div class="timeframe-container selector-item">
      <span @click="toggleTimeframeSelector" class="timeframe-text">
        Timeframe: <strong>{{ selectedTimeframeDisplay || "N/A" }}</strong>
        <span class="dropdown-arrow" :class="{ open: showTimeframeSelector }">
          &#9662;</span
        >
      </span>
      <ul v-if="showTimeframeSelector" class="timeframe-dropdown">
        <li
          v-for="tf in availableTimeframes"
          :key="tf"
          @click="selectTimeframe(tf)"
          :class="{ active: tf === selectedTimeframe }"
        >
          {{ tf }}
        </li>
        <li
          v-if="!availableTimeframes || availableTimeframes.length === 0"
          class="no-timeframes"
        >
          No timeframes available
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: "AssetTimeframeSelector",
  props: {
    asset: {
      type: String,
      default: "N/A",
    },
    timeframe: {
      // This prop represents the currently active timeframe
      type: String,
      default: "N/A",
    },
    availableTimeframes: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      isEditingAsset: false,
      editableAsset: "",
      showTimeframeSelector: false,
      selectedTimeframe: this.timeframe, // Initialize with prop
    };
  },
  computed: {
    selectedTimeframeDisplay() {
      return this.selectedTimeframe === "N/A"
        ? this.timeframe
        : this.selectedTimeframe;
    },
  },
  watch: {
    timeframe(newVal) {
      // Keep internal selectedTimeframe in sync if prop changes externally
      this.selectedTimeframe = newVal;
    },
  },
  methods: {
    editAsset() {
      this.editableAsset = this.asset === "N/A" ? "" : this.asset;
      this.isEditingAsset = true;
      this.$nextTick(() => {
        if (this.$refs.assetInput) {
          this.$refs.assetInput.focus();
        }
      });
    },
    saveAsset() {
      if (this.isEditingAsset) {
        const newAsset = this.editableAsset.trim().toUpperCase();
        if (newAsset && newAsset !== this.asset) {
          this.$emit("asset-updated", newAsset);
        }
        this.isEditingAsset = false;
      }
    },
    toggleTimeframeSelector() {
      this.showTimeframeSelector = !this.showTimeframeSelector;
    },
    selectTimeframe(tf) {
      this.selectedTimeframe = tf;
      this.showTimeframeSelector = false;
      if (tf !== this.timeframe) {
        // Only emit if changed from the prop value
        this.$emit("timeframe-updated", tf);
      }
    },
    // Helper to close dropdown if clicked outside - optional enhancement
    // handleClickOutside(event) {
    //   if (this.$el.contains(event.target)) return;
    //   this.showTimeframeSelector = false;
    // },
  },
  // mounted() {
  //   document.addEventListener('click', this.handleClickOutside, true);
  // },
  // beforeDestroy() {
  //   document.removeEventListener('click', this.handleClickOutside, true);
  // },
};
</script>

<style scoped>
.asset-timeframe-selector-display {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 8px 12px;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  font-size: 0.9em;
  position: relative; /* For dropdown positioning */
}

.selector-item {
  color: #495057;
}

.selector-item strong {
  color: #212529;
  font-weight: 600;
}

.asset-input {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  font-size: 0.9em;
  padding: 4px 6px;
  border: 1px solid #777;
  border-radius: 3px;
  color: #212529;
  font-weight: 600;
  width: 100px;
}

.timeframe-container {
  position: relative;
}

.timeframe-text {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.dropdown-arrow {
  margin-left: 5px;
  font-size: 0.7em;
  transition: transform 0.2s ease-in-out;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.timeframe-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  background-color: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  list-style: none;
  padding: 5px 0;
  margin: 5px 0 0 0;
  z-index: 1000;
  min-width: 100px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.timeframe-dropdown li {
  padding: 8px 12px;
  cursor: pointer;
  white-space: nowrap;
}

.timeframe-dropdown li:hover {
  background-color: #e9ecef;
}

.timeframe-dropdown li.active {
  background-color: #007bff;
  color: white;
  font-weight: bold;
}

.no-timeframes {
  color: #6c757d;
  font-style: italic;
  padding: 8px 12px;
}
</style>
