<!--
Custom Demo Overlay for LEStrADE.
Provides broad area highlighting via SVG mask and a precise pulsing pointer for actions.
-->
<template>
  <div v-if="active" class="demo-overlay" :class="{ 'has-clickable-element': !!clickableElementSelector }">
    <!-- SVG Mask for broad highlight -->
    <svg class="demo-mask">
      <defs>
        <mask id="demo-mask-def">
          <rect width="100%" height="100%" fill="white" />
          <rect 
            v-if="visibleAreaBox" 
            :x="visibleAreaBox.x - 6" 
            :y="visibleAreaBox.y - 6" 
            :width="visibleAreaBox.width + 12" 
            :height="visibleAreaBox.height + 12" 
            rx="12"
            fill="black" 
          />
        </mask>
      </defs>
      <rect width="100%" height="100%" fill="rgba(0, 0, 0, 0.4)" mask="url(#demo-mask-def)" />
    </svg>

    <!-- Specific Animated Pointer (Arrow + Clickable Glow) -->
    <template v-if="clickableAreaBox">
        <!-- The static glow around the element -->
        <div 
          class="demo-clickable-glow"
          :style="{
            top: (clickableAreaBox.y - 4) + 'px',
            left: (clickableAreaBox.x - 4) + 'px',
            width: (clickableAreaBox.width + 8) + 'px',
            height: (clickableAreaBox.height + 8) + 'px'
          }"
        ></div>

        <!-- The directional bouncing arrow -->
        <div 
          class="demo-pointer-arrow"
          :style="arrowStyle"
        >
            <div class="bouncing-arrow" :class="arrowClass">
                <v-icon color="primary" size="40">{{ arrowIcon }}</v-icon>
            </div>
        </div>
    </template>

    <!-- Popover / Tooltip -->
    <div 
      v-if="active"
      class="demo-popover"
      :style="popoverStyle"
    >
      <div class="demo-popover-header">{{ title }}</div>
      <div class="demo-popover-content">{{ content }}</div>
      <div class="demo-popover-actions justify-center">
        <div class="demo-pager d-flex align-center">
          <v-btn 
              icon 
              x-small 
              @click="onPrev" 
              :disabled="isFirst" 
              class="mr-2"
          >
              <v-icon>mdi-chevron-left</v-icon>
          </v-btn>
          
          <div class="demo-step-counter">{{ stepNumber }} of {{ totalSteps }}</div>
          
          <v-btn 
              icon
              x-small 
              @click="onNext" 
              v-if="!isLast"
              class="ml-2"
          >
              <v-icon>mdi-chevron-right</v-icon>
          </v-btn>
          
          <v-btn 
              color="primary" 
              text
               
              @click="onComplete" 
              v-else
              class="ml-6 font-weight-bold"
          >
            FINISH 🎉
          </v-btn>
        </div>
      </div>
    </div>

    <!-- Exit Demo button (X icon in top right below nav bar) -->
    <div class="demo-exit-button-wrapper">
      <v-btn
        icon
        large
        color="white"
        @click="onComplete"
        title="Exit Demo"
      >
        <v-icon large>mdi-close</v-icon>
      </v-btn>
    </div>

    <!-- The Shield: Blocks clicks outside the specific interaction area -->
    <!-- mousedown.stop.prevent is key to preventing v-menu from closing on outside click -->
    <div 
      class="demo-shield" 
      @mousedown.stop.prevent="onShieldClick"
      @mouseup.stop.prevent
      @click.stop.prevent
      @contextmenu.stop.prevent
    ></div>
  </div>
</template>

<script>
import EventBus from '@/event-bus.js'
import DemoController from '@/demo/DemoController.js'

export default {
  data() {
    return {
      active: false,
      currentStepId: null,
      title: '',
      content: '',
      visibleElementsSelector: '',
      clickableElementSelector: '',
      blockedElementsSelectors: [],
      visibleAreaBox: null,
      clickableAreaBox: null,
      arrowPosition: null, // manual override: 'top', 'bottom', 'left', 'right'
      finishButtonText: null,
      isFirst: true,
      isLast: false,
      stepNumber: 0,
      totalSteps: 0,
      refreshInterval: null
    }
  },
  computed: {
    effectiveArrowPosition() {
        if (this.arrowPosition) return this.arrowPosition
        if (!this.clickableAreaBox) return 'right'
        
        // Auto-calculate: if element is on left half, arrow on right. Else arrow on left.
        const centerX = this.clickableAreaBox.x + this.clickableAreaBox.width / 2
        return centerX < window.innerWidth / 2 ? 'right' : 'left'
    },
    arrowIcon() {
        switch (this.effectiveArrowPosition) {
            case 'left': return 'mdi-arrow-right-bold'
            case 'right': return 'mdi-arrow-left-bold'
            case 'top': return 'mdi-arrow-down-bold'
            case 'bottom': return 'mdi-arrow-up-bold'
            default: return 'mdi-arrow-left-bold'
        }
    },
    arrowClass() {
        return `bounce-${this.effectiveArrowPosition}`
    },
    arrowStyle() {
        if (!this.clickableAreaBox) return {}
        const box = this.clickableAreaBox
        const pos = this.effectiveArrowPosition
        
        let top, left;
        const offset = 60; // distance from element
        
        if (pos === 'left') {
            top = box.y + box.height / 2
            left = box.x - offset
        } else if (pos === 'right') {
            top = box.y + box.height / 2
            left = box.x + box.width + offset
        } else if (pos === 'top') {
            top = box.y - offset
            left = box.x + box.width / 2
        } else { // bottom
            top = box.y + box.height + offset
            left = box.x + box.width / 2
        }
        
        return {
            top: top + 'px',
            left: left + 'px'
        }
    },
    popoverStyle() {
      if (!this.visibleAreaBox) {
        return {
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          position: 'fixed'
        }
      }
      
      const box = this.visibleAreaBox
      const popoverWidth = 360
      const popoverHeight = 220 // Estimated average height
      const margin = 24
      
      const canFitBelow = window.innerHeight - (box.y + box.height) > popoverHeight + margin
      const canFitAbove = box.y > popoverHeight + margin
      const canFitRight = window.innerWidth - (box.x + box.width) > popoverWidth + margin
      const canFitLeft = box.x > popoverWidth + margin
      
      let top, left;
      
      if (canFitBelow) {
        top = box.y + box.height + margin
        left = Math.max(margin, Math.min(window.innerWidth - popoverWidth - margin, box.x))
      } else if (canFitAbove) {
        top = box.y - popoverHeight - margin
        left = Math.max(margin, Math.min(window.innerWidth - popoverWidth - margin, box.x))
      } else if (canFitRight) {
        top = Math.max(margin, Math.min(window.innerHeight - popoverHeight - margin, box.y))
        left = box.x + box.width + margin
      } else if (canFitLeft) {
        top = Math.max(margin, Math.min(window.innerHeight - popoverHeight - margin, box.y))
        left = box.x - popoverWidth - margin
      } else {
        // Absolute fallback: place in a corner that has the most space
        top = box.y > window.innerHeight / 2 ? margin : window.innerHeight - popoverHeight - margin
        left = box.x > window.innerWidth / 2 ? margin : window.innerWidth - popoverWidth - margin
      }
        
      return {
        top: top + 'px',
        left: left + 'px'
      }
    }
  },
  methods: {
    updateBoxes() {
      const selectors = Array.isArray(this.visibleElementsSelector) ? this.visibleElementsSelector : [this.visibleElementsSelector]
      
      let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity;
      let found = false;

      selectors.forEach(sel => {
          if (!sel || sel === 'body') return
          const el = document.querySelector(sel)
          if (el) {
              const rect = el.getBoundingClientRect()
              if (rect.width > 0 && rect.height > 0) {
                  found = true;
                  if (rect.x < minX) minX = rect.x;
                  if (rect.y < minY) minY = rect.y;
                  if (rect.x + rect.width > maxX) maxX = rect.x + rect.width;
                  if (rect.y + rect.height > maxY) maxY = rect.y + rect.height;
              }
          }
      })

      let newVisibleBox = null;
      if (found) {
          newVisibleBox = {
              x: minX,
              y: minY,
              width: maxX - minX,
              height: maxY - minY
          }
      }

      if (JSON.stringify(newVisibleBox) !== JSON.stringify(this.visibleAreaBox)) {
          this.visibleAreaBox = newVisibleBox
      }
      
      const clickableEl = this.clickableElementSelector ? document.querySelector(this.clickableElementSelector) : null
      if (clickableEl) {
        const rect = clickableEl.getBoundingClientRect()
        if (!this.clickableAreaBox || this.clickableAreaBox.x !== rect.x || this.clickableAreaBox.y !== rect.y) {
          this.clickableAreaBox = rect
        }{ name: 'Home' }
      } else {
        this.clickableAreaBox = null
      }

      // "Force Menu Open" logic for Step 3
      // ONLY trigger if we are actively on the HIDE_TIMELINE_DATA step
      if (this.active && this.currentStepId === 'HIDE_TIMELINE_DATA') {
          const menuVisible = document.querySelector('.menuable__content__active')
          if (!menuVisible) {
              const menuActivator = document.querySelector('#tsTimelineChipMenu')
              if (menuActivator) {
                  console.log('[DemoOverlay] Menu closed during Step 3, re-opening');
                  menuActivator.click()
              }
          }
      }
    },
    onNext() {
      EventBus.$emit('demo:action', 'next-click')
    },
    onPrev() {
      EventBus.$emit('demo:action', 'prev-click')
    },
    onComplete() {
      EventBus.$emit('demo:action', 'complete')
    },
    onShieldClick(e) {
        // High Priority: If a specific element is clickable, strictly ONLY allow clicks there.
        if (this.clickableAreaBox) {
            const b = this.clickableAreaBox
            const isInside = e.clientX >= b.x && e.clientX <= b.x + b.width &&
                             e.clientY >= b.y && e.clientY <= b.y + b.height
            
            if (isInside) {
                this.passClickThrough(e.clientX, e.clientY)
            }
            
        }
    },
    passClickThrough(x, y) {
        const shield = this.$el.querySelector('.demo-shield')
        shield.style.display = 'none'
        const targetEl = document.elementFromPoint(x, y)
        shield.style.display = 'block'
        
        // Block clicks if they fall within an explicitly forbidden selector for this step
        if (targetEl && this.blockedElementsSelectors && this.blockedElementsSelectors.length > 0) {
            const isBlocked = this.blockedElementsSelectors.some(sel => targetEl.closest(sel))
            if (isBlocked) {
                return
            }
        }

        if (targetEl) {
            // Restore standard click behavior (bubbles: true) so UI reacts correctly
            targetEl.click()
            
            if (targetEl.tagName === 'INPUT' || targetEl.tagName === 'TEXTAREA') {
                targetEl.focus()
            }
        }
        
        // Re-calculate immediately after interaction to catch UI changes (like menu collapse)
        this.$nextTick(() => this.updateBoxes())
    },
    handleKeydown(e) {
        if (!this.active) return
        
        if (e.key === 'ArrowRight') {
            if (!this.isLast) this.onNext()
        } else if (e.key === 'ArrowLeft') {
            if (!this.isFirst) this.onPrev()
        }
    }
  },
  mounted() {
    window.addEventListener('keydown', this.handleKeydown)
    
    const handleUpdate = (data) => {
      // Clear boxes immediately to prevent "ghosting" from the previous step
      this.visibleAreaBox = null
      this.clickableAreaBox = null

      if (!data) {
        this.active = false
        this.currentStepId = null
        if (this.refreshInterval) clearInterval(this.refreshInterval)
        this.refreshInterval = null
        return
      }
      
      this.active = true
      this.currentStepId = data.id
      this.title = data.title
      this.content = data.content
      this.visibleElementsSelector = data.visibleElements
      this.clickableElementSelector = data.clickableElement
      this.blockedElementsSelectors = data.blockedElements || []
      this.arrowPosition = data.arrowPosition
      this.finishButtonText = data.finishButtonText
      this.isFirst = data.isFirst
      this.isLast = data.isLast
      this.stepNumber = data.stepNumber
      this.totalSteps = data.totalSteps
      
      this.$nextTick(() => {
        this.updateBoxes()
        if (!this.refreshInterval) {
          // Increase frequency to 16ms (approx 60fps) for smoother tracking
          this.refreshInterval = setInterval(this.updateBoxes, 16)
        }
      })
    }

    EventBus.$on('demo:update-ui', handleUpdate)

    // Pull initial state immediately to catch up if we mounted late (fix hard refresh race)
    const initialState = DemoController.getCurrentUiState()
    if (initialState) {
        console.log('[DemoOverlay] Catching up with initial state:', initialState.id);
        handleUpdate(initialState)
    }
  },
  beforeDestroy() {
    window.removeEventListener('keydown', this.handleKeydown)
    if (this.refreshInterval) clearInterval(this.refreshInterval)
    EventBus.$off('demo:update-ui')
  }
}
</script>

<style scoped lang="scss">
.demo-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 20000;
  pointer-events: none;
}

.demo-exit-button-wrapper {
  position: absolute;
  top: 36px;
  right: 36px;
  z-index: 20002;
  pointer-events: auto;
}

.demo-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.demo-shield {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: auto;
    background: transparent;
    z-index: 19999;
}

.demo-clickable-glow {
    position: absolute;
    border: 2px solid #1976d2;
    border-radius: 8px;
    pointer-events: none;
    z-index: 10001;
    box-shadow: 0 0 15px rgba(25, 118, 210, 0.6);
}

.demo-pointer-arrow {
  position: absolute;
  width: 40px;
  height: 40px;
  margin-top: -20px;
  margin-left: -20px;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
  
  .bouncing-arrow {
    position: absolute;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
  }
}

@keyframes demo-bounce-right {
  0% { transform: translateX(0); }
  100% { transform: translateX(15px); }
}

@keyframes demo-bounce-left {
  0% { transform: translateX(0); }
  100% { transform: translateX(-15px); }
}

@keyframes demo-bounce-top {
  0% { transform: translateY(0); }
  100% { transform: translateY(-15px); }
}

@keyframes demo-bounce-bottom {
  0% { transform: translateY(0); }
  100% { transform: translateY(15px); }
}

.bounce-right { animation: demo-bounce-right 0.8s infinite alternate ease-in-out; }
.bounce-left { animation: demo-bounce-left 0.8s infinite alternate ease-in-out; }
.bounce-top { animation: demo-bounce-top 0.8s infinite alternate ease-in-out; }
.bounce-bottom { animation: demo-bounce-bottom 0.8s infinite alternate ease-in-out; }

.demo-popover {
  position: absolute;
  width: 360px;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.3);
  pointer-events: auto;
  z-index: 20001;
  transition: top 0.2s ease, left 0.2s ease;
  border: 1px solid rgba(0,0,0,0.05);
  
  &-header {
    font-weight: 800;
    font-size: 1.2em;
    margin-bottom: 10px;
    color: #1976d2;
    letter-spacing: -0.5px;
  }
  
  &-content {
    font-size: 1em;
    line-height: 1.5;
    color: #444;
    margin-bottom: 20px;
    white-space: pre-line;
  }
  
  &-actions {
    display: flex;
    align-items: center;
    border-top: 1px solid #f0f0f0;
    padding-top: 15px;
  }

  .demo-step-counter {
      font-size: 0.85em;
      color: #888;
      font-weight: 600;
  }
}
</style>
