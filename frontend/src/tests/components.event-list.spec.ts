import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import EventList from "@/components/shared/EventList.vue";

describe("EventList", () => {
  it("renders danmaku events with Chinese guard identity labels", () => {
    const wrapper = mount(EventList, {
      props: {
        events: [
          {
            event_type: "danmaku",
            uname: "弹幕用户",
            timestamp: 1710000000,
            payload: {
              msg: "这是测试弹幕",
              guard_level: 2,
            },
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("弹幕用户 · 普通弹幕");
    expect(wrapper.text()).toContain("提督");
    expect(wrapper.text()).toContain("这是测试弹幕");
  });

  it("renders gift events with quantity and price summary", () => {
    const wrapper = mount(EventList, {
      props: {
        events: [
          {
            event_type: "gift",
            uname: "送礼用户",
            timestamp: 1710000000,
            payload: {
              gift_name: "小心心",
              gift_num: 3,
              price: 10,
              r_price: 30,
            },
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("送礼用户 · 礼物事件");
    expect(wrapper.text()).toContain("小心心 x 3");
    expect(wrapper.text()).toContain("单价 10 · 总价值 30");
  });

  it("renders like events with count and Chinese event labels", () => {
    const wrapper = mount(EventList, {
      props: {
        events: [
          {
            event_type: "like",
            uname: "测试用户",
            timestamp: 1710000000,
            payload: {
              like_text: "点赞",
              like_count: 12,
            },
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("测试用户 · 点赞事件");
    expect(wrapper.text()).toContain("点赞 (12)");
  });

  it("renders control events with Chinese labels", () => {
    const wrapper = mount(EventList, {
      props: {
        events: [
          {
            type: "bluetooth_trigger",
            timestamp: 1710000000,
            payload: {
              waveform_name: "舒缓波形",
              message: "已处理",
            },
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("蓝牙触发");
    expect(wrapper.text()).toContain("已处理");
  });
});
