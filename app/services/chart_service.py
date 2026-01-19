"""Chart generation service using Matplotlib."""

import io
import logging
from typing import Dict, List, Optional, Tuple, Any

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


class ChartService:
    """Service for generating various chart types."""

    def __init__(self):
        """Initialize chart service with default settings."""
        self.default_colors = [
            '#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B',
            '#95C623', '#5C4D7D', '#E84855', '#F9DC5C', '#3185FC'
        ]
        self.figure_dpi = 150

    def create_bar_chart(
        self,
        data: Dict[str, Any],
        title: str = "Bar Chart",
        xlabel: str = "",
        ylabel: str = "Value"
    ) -> bytes:
        """
        Create a bar chart from data.

        Args:
            data: Dictionary with labels as keys and values as values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label

        Returns:
            PNG image bytes
        """
        fig, ax = plt.subplots(figsize=(10, 6), dpi=self.figure_dpi)

        labels = list(data.keys())
        values = [float(v) if isinstance(v, (int, float)) else 0 for v in data.values()]
        colors = self.default_colors[:len(labels)]

        bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=1.2)

        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.annotate(
                f'{value:.1f}' if isinstance(value, float) else str(int(value)),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha='center', va='bottom',
                fontsize=10, fontweight='bold'
            )

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def create_pie_chart(
        self,
        data: Dict[str, Any],
        title: str = "Pie Chart"
    ) -> bytes:
        """
        Create a pie chart from data.

        Args:
            data: Dictionary with labels as keys and values as values
            title: Chart title

        Returns:
            PNG image bytes
        """
        fig, ax = plt.subplots(figsize=(10, 8), dpi=self.figure_dpi)

        labels = list(data.keys())
        values = [float(v) if isinstance(v, (int, float)) else 0 for v in data.values()]
        colors = self.default_colors[:len(labels)]

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            colors=colors,
            explode=[0.02] * len(labels),
            shadow=True,
            startangle=90
        )

        # Enhance text appearance
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.axis('equal')

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def create_line_chart(
        self,
        data: Dict[str, List[float]],
        title: str = "Line Chart",
        xlabel: str = "X",
        ylabel: str = "Y"
    ) -> bytes:
        """
        Create a line chart from data.

        Args:
            data: Dictionary with series names as keys and lists of values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label

        Returns:
            PNG image bytes
        """
        fig, ax = plt.subplots(figsize=(10, 6), dpi=self.figure_dpi)

        for idx, (label, values) in enumerate(data.items()):
            if isinstance(values, list):
                x = range(len(values))
                y = values
            else:
                x = [0]
                y = [values]

            color = self.default_colors[idx % len(self.default_colors)]
            ax.plot(x, y, marker='o', linewidth=2, markersize=6,
                   label=label, color=color)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def create_radar_chart(
        self,
        data: Dict[str, Any],
        title: str = "Radar Chart"
    ) -> bytes:
        """
        Create a radar/spider chart from data.

        Args:
            data: Dictionary with categories as keys and values
            title: Chart title

        Returns:
            PNG image bytes
        """
        fig, ax = plt.subplots(figsize=(10, 8), dpi=self.figure_dpi,
                               subplot_kw=dict(polar=True))

        labels = list(data.keys())
        values = [float(v) if isinstance(v, (int, float)) else 0 for v in data.values()]

        # Number of variables
        num_vars = len(labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

        # Complete the loop
        values = values + values[:1]
        angles = angles + angles[:1]

        ax.plot(angles, values, 'o-', linewidth=2, color=self.default_colors[0])
        ax.fill(angles, values, alpha=0.25, color=self.default_colors[0])

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def create_chart(
        self,
        chart_type: str,
        data: Dict[str, Any],
        title: str = "Chart",
        **kwargs
    ) -> bytes:
        """
        Create a chart based on the specified type.

        Args:
            chart_type: Type of chart (bar, pie, line, radar)
            data: Chart data
            title: Chart title
            **kwargs: Additional arguments for specific chart types

        Returns:
            PNG image bytes
        """
        chart_methods = {
            'bar': self.create_bar_chart,
            'pie': self.create_pie_chart,
            'line': self.create_line_chart,
            'radar': self.create_radar_chart
        }

        method = chart_methods.get(chart_type.lower(), self.create_bar_chart)
        return method(data, title=title, **kwargs)

    def _fig_to_bytes(self, fig: plt.Figure) -> bytes:
        """Convert matplotlib figure to PNG bytes."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()


# Singleton instance
chart_service = ChartService()
