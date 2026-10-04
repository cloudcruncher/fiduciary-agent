"""Manim scene for the gateway explainer. Scene lengths match the table in script.md.

Render: uv run --with manim manim -ql docs/explain/video/scene.py GatewayStory
"""
from manim import (
    BLUE,
    DOWN,
    GREEN,
    GREY,
    LEFT,
    RED,
    RIGHT,
    UP,
    YELLOW,
    Arrow,
    Create,
    FadeIn,
    FadeOut,
    RoundedRectangle,
    Scene,
    Text,
    VGroup,
    Write,
)


# Scene end times in seconds (see script.md). Narration is laid over these.
SCENE_ENDS = (8, 20, 34, 48, 60, 80)


def box(label, color=BLUE, w=2.6, h=0.9):
    r = RoundedRectangle(corner_radius=0.15, width=w, height=h, color=color)
    t = Text(label, font_size=22).move_to(r)
    return VGroup(r, t)


class GatewayStory(Scene):
    def hold_until(self, n):
        """Wait until scene n (1-based) reaches its end time."""
        self.wait(max(0.05, SCENE_ENDS[n - 1] - self.renderer.time))

    def construct(self):
        # 1. The question
        q = box("Can I afford a holiday?", YELLOW, w=4.2).to_edge(UP)
        self.play(FadeIn(q))
        self.hold_until(1)

        # 2. Prompt Guard
        guard = box("Prompt Guard", BLUE).next_to(q, DOWN, buff=0.9)
        a1 = Arrow(q.get_bottom(), guard.get_top(), buff=0.1)
        self.play(Create(a1), FadeIn(guard))
        bad = Text('"ignore all rules"', font_size=20, color=RED).to_edge(LEFT).shift(UP)
        blocked = Arrow(bad.get_right(), guard.get_left() + LEFT * 0.8, color=RED, buff=0.1)
        x = Text("X  blocked", font_size=22, color=RED).next_to(blocked, DOWN, buff=0.15)
        self.play(FadeIn(bad), Create(blocked))
        self.play(Write(x))
        self.hold_until(2)
        self.play(FadeOut(bad), FadeOut(blocked), FadeOut(x))

        # 3. Verified data
        data = box("Verified data", GREEN, w=3.2).next_to(guard, DOWN, buff=0.9)
        a2 = Arrow(guard.get_bottom(), data.get_top(), buff=0.1)
        tools = VGroup(*[Text(t, font_size=18, color=GREY) for t in ("bank rate", "your spending", "your credit")])
        tools.arrange(RIGHT, buff=0.7).next_to(data, DOWN, buff=0.5)
        self.play(Create(a2), FadeIn(data))
        self.play(FadeIn(tools))
        self.hold_until(3)

        # 4. Gateway -> local model, cloud greyed
        self.play(*[FadeOut(m) for m in (q, a1, guard, a2, tools)])
        data_top = data.copy().to_edge(UP)
        self.play(data.animate.move_to(data_top))
        gw = box("AI Gateway", BLUE).next_to(data, DOWN, buff=0.8)
        local = box("Model on your Mac", GREEN, w=3.2).next_to(gw, DOWN, buff=0.8).shift(LEFT * 2)
        cloud = box("Cloud", GREY, w=2.0).next_to(gw, DOWN, buff=0.8).shift(RIGHT * 3)
        g_in = Arrow(data.get_bottom(), gw.get_top(), buff=0.1)
        g_loc = Arrow(gw.get_bottom(), local.get_top(), color=GREEN, buff=0.1)
        g_cld = Arrow(gw.get_bottom(), cloud.get_top(), color=GREY, buff=0.1)
        self.play(FadeIn(gw), Create(g_in))
        self.play(FadeIn(local), Create(g_loc), FadeIn(cloud), Create(g_cld))
        self.hold_until(4)

        # 5. Failover
        self.play(gw[0].animate.set_color(RED))
        direct = Arrow(data.get_left(), local.get_left(), color=GREEN, buff=0.1, path_arc=1.2)
        note = Text("Gateway down: call the local model directly", font_size=20, color=GREEN)
        note.to_edge(DOWN)
        self.play(Create(direct), Write(note))
        self.hold_until(5)

        # 6. Answer
        self.play(*[FadeOut(m) for m in self.mobjects])
        ans = VGroup(
            Text("£3,700 left", font_size=44, color=GREEN),
            Text("Runway: 62 days", font_size=32),
        ).arrange(DOWN, buff=0.3)
        self.play(Write(ans))
        self.hold_until(6)
