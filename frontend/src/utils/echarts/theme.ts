// src/utils/echarts/theme.ts
import * as echarts from 'echarts/core';

// 现代 SaaS 卡片风配色体系
const colorPalette = [
  '#2563eb', // brand-1 (主蓝)
  '#16a34a', // success-1 (绿)
  '#f59e0b', // warning-1 (黄)
  '#ef4444', // danger-1 (红)
  '#8b5cf6', // 紫
  '#06b6d4', // 青
  '#ec4899', // 粉
  '#f97316', // 橙
  '#14b8a6'  // 蓝绿
];

export const saasTheme = {
  color: colorPalette,
  backgroundColor: 'transparent',
  
  textStyle: {
    fontFamily: 'inherit',
    color: '#606266' // var(--text-2)
  },

  title: {
    textStyle: {
      color: '#303133', // var(--text-1)
      fontWeight: 600
    },
    subtextStyle: {
      color: '#909399' // var(--text-3)
    }
  },

  tooltip: {
    backgroundColor: '#ffffff',
    borderColor: '#e5eaf0',
    textStyle: {
      color: '#303133'
    },
    axisPointer: {
      lineStyle: {
        color: '#dcdfe6'
      },
      crossStyle: {
        color: '#dcdfe6'
      }
    }
  },

  grid: {
    top: 40,
    right: 20,
    bottom: 20,
    left: 40,
    containLabel: true
  },

  categoryAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: '#e5eaf0' // var(--border-1)
      }
    },
    axisTick: {
      show: false
    },
    axisLabel: {
      show: true,
      color: '#909399'
    },
    splitLine: {
      show: false
    },
    splitArea: {
      show: false
    }
  },

  valueAxis: {
    axisLine: {
      show: false
    },
    axisTick: {
      show: false
    },
    axisLabel: {
      show: true,
      color: '#909399'
    },
    splitLine: {
      show: true,
      lineStyle: {
        type: 'dashed',
        color: '#ebeef5'
      }
    },
    splitArea: {
      show: false
    }
  },

  line: {
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    itemStyle: {
      borderWidth: 2
    },
    lineStyle: {
      width: 3
    }
  },

  bar: {
    itemStyle: {
      borderRadius: [4, 4, 0, 0]
    }
  },

  pie: {
    itemStyle: {
      borderWidth: 2,
      borderColor: '#ffffff'
    }
  },

  radar: {
    axisLine: {
      lineStyle: {
        color: '#e5eaf0'
      }
    },
    splitLine: {
      lineStyle: {
        color: '#ebeef5'
      }
    },
    splitArea: {
      show: true,
      areaStyle: {
        color: ['rgba(245, 247, 250, 0.5)', 'rgba(255, 255, 255, 0.5)']
      }
    },
    itemStyle: {
      borderWidth: 2
    }
  }
};

// 注册主题
export const registerTheme = () => {
  echarts.registerTheme('saas', saasTheme);
};
