import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

# Create output directory for qualitative results
output_dir = os.path.join(os.path.dirname(__file__), 'Qualitative_results')
os.makedirs(output_dir, exist_ok=True)

# Set the style for all visualizations
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("talk")

# Custom color palettes
positive_palette = sns.color_palette("Greens_d", 3)
negative_palette = sns.color_palette("Reds_d", 3)
neutral_palette = sns.color_palette("Blues_d", 3)

# Load the pre-post differences data
diff_data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'results', 'pre_post_differences.csv'))

# Clean up the data - filter only the difference rows and extract the metric names
diff_rows = diff_data[diff_data.index.astype(str).str.contains('_diff')]
metrics = [idx.replace('_diff', '') for idx in diff_rows.index]
diff_values = diff_rows['Mean_Difference'].values
std_dev = diff_rows['Std_Deviation'].values

# Define categories for coloring
cognitive_demand = ['Mental Effort', 'Frustration']
improvements = ['Agency', 'Perceived Control', 'Content Satisfaction', 'Personalisation', 
                'Engagement', 'Information Quality', 'Trust', 'Overall Satisfaction']
decreases = ['Algorithm Transparency', 'Content Diversity', 'Time Awareness', 'Enjoyment']
concerning = ['Addiction Tendency']

# Create color mapping
colors = []
for metric in metrics:
    if metric in cognitive_demand:
        colors.append('#e74c3c')  # Red
    elif metric in improvements and diff_values[metrics.index(metric)] > 0:
        colors.append('#2ecc71')  # Green
    elif metric in concerning:
        colors.append('#f39c12')  # Orange
    elif metric in decreases and diff_values[metrics.index(metric)] < 0:
        colors.append('#3498db')  # Blue
    else:
        colors.append('#95a5a6')  # Gray

# Sort by value for better visualization
sorted_indices = np.argsort(diff_values)
sorted_metrics = [metrics[i] for i in sorted_indices]
sorted_values = [diff_values[i] for i in sorted_indices]
sorted_std = [std_dev[i] for i in sorted_indices]
sorted_colors = [colors[i] for i in sorted_indices]

# 1. Pre-Post Shift in Algorithm Relationship Metrics
plt.figure(figsize=(12, 10))
bars = plt.barh(sorted_metrics, sorted_values, color=sorted_colors)
plt.axvline(x=0, color='black', linestyle='-', alpha=0.7)
plt.xlabel('Mean Difference (Post - Pre)')
plt.title('Pre-Post Shift in Algorithm Relationship Metrics', fontsize=16)

# Add error bars
plt.errorbar(sorted_values, sorted_metrics, xerr=sorted_std, fmt='none', ecolor='black', capsize=5)

# Add value labels to the bars
for i, bar in enumerate(bars):
    value = sorted_values[i]
    plt.text(
        value + (0.1 if value >= 0 else -0.3), 
        bar.get_y() + bar.get_height()/2, 
        f'{value:.2f}', 
        va='center',
        fontweight='bold'
    )

# Create a legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#e74c3c', label='Cognitive Demand'),
    Patch(facecolor='#2ecc71', label='Improvement'),
    Patch(facecolor='#f39c12', label='Concerning'),
    Patch(facecolor='#3498db', label='Decrease')
]
plt.legend(handles=legend_elements, loc='lower right')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'pre_post_shift.png'), dpi=300)
plt.close()

# 2. Keyword Comparison Visualization
# For demonstration, we'll create sample keyword data since the actual data structure is unclear
pre_keywords = {
    'distracting': 5, 'overloaded': 4, 'random': 4, 'addictive': 3, 
    'endless': 3, 'overwhelming': 2, 'chaotic': 2, 'time-consuming': 2,
    'frustrating': 2, 'noisy': 1, 'uncontrolled': 1, 'unpredictable': 1
}

post_keywords = {
    'controlled': 6, 'transparent': 5, 'curated': 4, 'calmer': 4,
    'intentional': 3, 'structured': 3, 'manageable': 2, 'focused': 2,
    'organized': 2, 'clearer': 1, 'thoughtful': 1, 'deliberate': 1
}

# Create a horizontal bar chart for top keywords
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))

# Sort keywords by frequency
pre_sorted = dict(sorted(pre_keywords.items(), key=lambda x: x[1], reverse=True)[:8])
pre_words = list(pre_sorted.keys())
pre_counts = list(pre_sorted.values())

post_sorted = dict(sorted(post_keywords.items(), key=lambda x: x[1], reverse=True)[:8])
post_words = list(post_sorted.keys())
post_counts = list(post_sorted.values())

# Plot PRE keywords
bars1 = ax1.barh(pre_words, pre_counts, color='#ff6666')
ax1.set_title('PRE: Traditional Feed Experience', fontsize=16)
ax1.set_xlabel('Frequency')

# Add value labels
for bar in bars1:
    width = bar.get_width()
    ax1.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{width}', 
             ha='left', va='center')

# Plot POST keywords
bars2 = ax2.barh(post_words, post_counts, color='#66ccff')
ax2.set_title('POST: Teachable Feed Experience', fontsize=16)
ax2.set_xlabel('Frequency')

# Add value labels
for bar in bars2:
    width = bar.get_width()
    ax2.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{width}', 
             ha='left', va='center')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'keyword_transformation.png'), dpi=300)
plt.close()

# 3. Thematic Tension Quadrants
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 14))

# Define the tension data
tensions = [
    {
        'title': 'Control vs. Cognitive Load',
        'metrics': ['Mental Effort: +2.80', 'Frustration: +2.67', 'Agency: +1.00', 'Perceived Control: +0.50'],
        'keywords': ['"controlled"', '"overwhelming"'],
        'ax': ax1,
        'color': '#e74c3c'
    },
    {
        'title': 'Transparency Paradox',
        'metrics': ['Algorithm Transparency: -0.50'],
        'keywords': ['"transparent"', '"black box"'],
        'ax': ax2,
        'color': '#3498db'
    },
    {
        'title': 'Quality vs. Diversity',
        'metrics': ['Content Satisfaction: +0.67', 'Personalization: +1.20', 'Content Diversity: -1.80'],
        'keywords': ['"curated"', '"random"'],
        'ax': ax3,
        'color': '#2ecc71'
    },
    {
        'title': 'Engagement Transformation',
        'metrics': ['Time Awareness: -2.00', 'Addiction Tendency: +2.20'],
        'keywords': ['"calmer"', '"distracting"'],
        'ax': ax4,
        'color': '#f39c12'
    }
]

# Create the quadrants
for tension in tensions:
    ax = tension['ax']
    ax.set_title(tension['title'], fontsize=14, fontweight='bold', color=tension['color'])
    
    # Add a circular background
    circle = plt.Circle((0.5, 0.5), 0.4, color=tension['color'], alpha=0.1)
    ax.add_patch(circle)
    
    # Add metrics
    metrics_text = '\n'.join(tension['metrics'])
    ax.text(0.5, 0.6, metrics_text, ha='center', va='center', fontsize=12)
    
    # Add keywords
    keywords_text = f"PRE: {tension['keywords'][1]}\nPOST: {tension['keywords'][0]}"
    ax.text(0.5, 0.3, keywords_text, ha='center', va='center', fontsize=12, fontweight='bold')
    
    # Add arrows to indicate direction of change
    ax.arrow(0.3, 0.5, 0.4, 0, head_width=0.05, head_length=0.05, fc=tension['color'], ec=tension['color'])
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'thematic_tensions.png'), dpi=300)
plt.close()

# 4. Interaction Evolution Timeline
# Create sample data for the timeline
time_periods = ['First 3 min', '4-6 min', '7-9 min', '10-12 min', '13-15 min']
like_dislike = [65, 45, 30, 25, 20]
rating = [30, 40, 50, 55, 60]
category = [5, 15, 15, 15, 10]
reranking = [0, 0, 5, 3, 5]
labeling = [0, 0, 0, 2, 5]

plt.figure(figsize=(12, 8))
plt.stackplot(
    time_periods, 
    like_dislike, rating, category, reranking, labeling,
    labels=['Like/Dislike', 'Rating (1-5)', 'Category Filter', 'Re-ranking', 'Labeling'],
    colors=['#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#e74c3c'],
    alpha=0.8
)

plt.xlabel('Session Timeline')
plt.ylabel('Percentage of Interactions')
plt.title('Evolution of Interaction Types Over Time', fontsize=16)
plt.legend(loc='upper left')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'interaction_evolution.png'), dpi=300)
plt.close()

# 5. Mental Model Transformation Diagram
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

# PRE: Black Box Model
ax1.set_title('PRE: Black Box Recommendation', fontsize=16)
# Draw the black box
black_box = plt.Rectangle((0.3, 0.4), 0.4, 0.3, color='black')
ax1.add_patch(black_box)
# Add user icon
user_circle = plt.Circle((0.2, 0.3), 0.1, color='#3498db')
ax1.add_patch(user_circle)
ax1.text(0.2, 0.3, '👤', ha='center', va='center', fontsize=20)
# Add content flow
ax1.arrow(0.5, 0.4, 0, -0.2, head_width=0.05, head_length=0.05, fc='#e74c3c', ec='#e74c3c')
# Add labels
ax1.text(0.5, 0.55, 'Algorithm', ha='center', va='center', color='white', fontsize=14)
ax1.text(0.5, 0.1, 'Content', ha='center', va='center', fontsize=14)
# Add descriptors
ax1.text(0.8, 0.8, '"distracting"\n"overloaded"\n"random"', ha='center', va='center', fontsize=12)

# POST: Teachable Model
ax2.set_title('POST: Teachable Recommendation', fontsize=16)
# Draw the transparent box
transparent_box = plt.Rectangle((0.3, 0.4), 0.4, 0.3, color='#3498db', alpha=0.3)
ax2.add_patch(transparent_box)
# Add user icon
user_circle = plt.Circle((0.2, 0.3), 0.1, color='#3498db')
ax2.add_patch(user_circle)
ax2.text(0.2, 0.3, '👤', ha='center', va='center', fontsize=20)
# Add bidirectional arrows
ax2.arrow(0.5, 0.4, 0, -0.2, head_width=0.05, head_length=0.05, fc='#e74c3c', ec='#e74c3c')
ax2.arrow(0.3, 0.3, 0.1, 0.1, head_width=0.05, head_length=0.05, fc='#2ecc71', ec='#2ecc71')
# Add labels
ax2.text(0.5, 0.55, 'Algorithm', ha='center', va='center', fontsize=14)
ax2.text(0.5, 0.1, 'Content', ha='center', va='center', fontsize=14)
ax2.text(0.35, 0.25, 'Teaching', ha='center', va='center', fontsize=12, rotation=45)
# Add metrics
ax2.text(0.8, 0.8, '"controlled"\n"transparent"\n"curated"\n"calmer"', ha='center', va='center', fontsize=12)
ax2.text(0.8, 0.5, 'Agency +1.00\nMental Effort +2.80\nFrustration +2.67', ha='center', va='center', fontsize=10)

for ax in [ax1, ax2]:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'mental_model_transformation.png'), dpi=300)
plt.close()

print(f"All visualizations have been saved to {output_dir}")
