import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import re

# Set plotting style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette('Set2')

class FeedAnalysis:
    def __init__(self, excel_path=os.path.join(os.path.dirname(__file__), 'merged_questionnaires.xlsx')):
        """
        Initialize the analysis with the path to the merged questionnaires Excel file.
        
        Parameters:
        -----------
        excel_path : str
            Path to the merged questionnaires Excel file
        """
        self.excel_path = excel_path
        self.pre_data = None
        self.post_data = None
        self.logs_data = None
        self.load_data()
        
        # Define column groups for analysis
        self.scale_cols_pre = []
        self.scale_cols_post = []
        
        if self.pre_data is not None:
            self.scale_cols_pre = [col for col in self.pre_data.columns if col.startswith('scale_responses_c')]
        
        if self.post_data is not None:
            self.scale_cols_post = [col for col in self.post_data.columns if col.startswith('scale_responses_pc')]
        
        # Map question numbers to their meaning (based on your research)
        self.pre_question_map = {
            'scale_responses_c1': 'Perceived Control',
            'scale_responses_c2': 'Algorithm Transparency',
            'scale_responses_c3': 'Content Satisfaction',
            'scale_responses_c4': 'Engagement',
            'scale_responses_c5': 'Frustration',
            'scale_responses_c6': 'Time Awareness',
            'scale_responses_c7': 'Agency',
            'scale_responses_c8': 'Content Diversity',
            'scale_responses_c9': 'Personalization',
            'scale_responses_c10': 'Mental Effort',
            'scale_responses_c11': 'Trust',
            'scale_responses_c12': 'Addiction Tendency',
            'scale_responses_c13': 'Information Quality',
            'scale_responses_c14': 'Enjoyment',
            'scale_responses_c15': 'Overall Satisfaction'
        }
        
        self.post_question_map = {
            'scale_responses_pc1': 'Perceived Control',
            'scale_responses_pc2': 'Algorithm Transparency',
            'scale_responses_pc3': 'Content Satisfaction',
            'scale_responses_pc4': 'Engagement',
            'scale_responses_pc5': 'Frustration',
            'scale_responses_pc6': 'Time Awareness',
            'scale_responses_pc7': 'Agency',
            'scale_responses_pc8': 'Content Diversity',
            'scale_responses_pc9': 'Personalization',
            'scale_responses_pc10': 'Mental Effort',
            'scale_responses_pc11': 'Trust',
            'scale_responses_pc12': 'Addiction Tendency',
            'scale_responses_pc13': 'Information Quality',
            'scale_responses_pc14': 'Enjoyment',
            'scale_responses_pc15': 'Overall Satisfaction'
        }
        
        # Create output directory
        self.output_dir = Path('results')
        self.output_dir.mkdir(exist_ok=True)
    
    def load_data(self):
        """Load data from the Excel file"""
        try:
            self.pre_data = pd.read_excel(self.excel_path, sheet_name='PRE Questionnaire')
            self.post_data = pd.read_excel(self.excel_path, sheet_name='POST Questionnaire')
            self.logs_data = pd.read_excel(self.excel_path, sheet_name='Session Logs')
            
            print(f"Loaded data: {len(self.pre_data)} pre-questionnaires, {len(self.post_data)} post-questionnaires")
            print(f"Session logs: {len(self.logs_data)} entries")
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def merge_pre_post_data(self):
        """Merge pre and post data by username for direct comparison"""
        # Check if data is available
        if self.pre_data is None or self.post_data is None:
            print("Error: Pre or Post data is not available. Cannot merge.")
            return None
            
        # Create a copy of relevant columns
        pre_scores = self.pre_data[['username', 'source'] + self.scale_cols_pre].copy()
        post_scores = self.post_data[['username', 'source'] + self.scale_cols_post].copy()
        
        # Rename post columns to match pre columns for easier comparison
        post_scores_renamed = post_scores.copy()
        rename_dict = {post_col: pre_col for post_col, pre_col in zip(self.scale_cols_post, self.scale_cols_pre)}
        post_scores_renamed.rename(columns=rename_dict, inplace=True)
        
        # Add suffix to distinguish pre and post
        pre_scores = pre_scores.add_suffix('_pre')
        pre_scores.rename(columns={'username_pre': 'username', 'source_pre': 'source'}, inplace=True)
        
        post_scores_renamed = post_scores_renamed.add_suffix('_post')
        post_scores_renamed.rename(columns={'username_post': 'username', 'source_post': 'source'}, inplace=True)
        
        # Merge on username
        merged_data = pd.merge(pre_scores, post_scores_renamed, on=['username', 'source'], how='inner')
        
        return merged_data
    
    def calculate_score_differences(self):
        """Calculate differences between pre and post scores"""
        merged_data = self.merge_pre_post_data()
        
        if merged_data is None:
            print("Error: Could not calculate score differences due to missing data.")
            return None
        
        # Calculate differences
        diff_data = pd.DataFrame(index=merged_data.index)
        diff_data['username'] = merged_data['username']
        diff_data['source'] = merged_data['source']
        
        for pre_col in self.scale_cols_pre:
            post_col = pre_col.replace('scale_responses_c', 'scale_responses_pc')
            diff_col = f"{self.pre_question_map[pre_col]}_diff"
            
            # Calculate post - pre difference
            diff_data[diff_col] = merged_data[f"{pre_col}_post"] - merged_data[f"{pre_col}_pre"]
        
        return diff_data
    
    def analyze_pre_post_differences(self):
        """Analyze the differences between pre and post questionnaire responses"""
        diff_data = self.calculate_score_differences()
        
        if diff_data is None:
            print("Error: Could not analyze differences due to missing data.")
            return pd.DataFrame()  # Return empty DataFrame instead of None
        
        # Calculate mean differences for each question
        mean_diffs = diff_data.drop(['username', 'source'], axis=1).mean()
        
        # Calculate standard deviation of differences
        std_diffs = diff_data.drop(['username', 'source'], axis=1).std()
        
        # Calculate statistical significance (simple t-test)
        from scipy import stats
        p_values = {}
        
        merged_data = self.merge_pre_post_data()
        for pre_col in self.scale_cols_pre:
            post_col = pre_col.replace('scale_responses_c', 'scale_responses_pc')
            question = self.pre_question_map[pre_col]
            
            pre_scores = merged_data[f"{pre_col}_pre"]
            post_scores = merged_data[f"{pre_col}_post"]
            
            # Paired t-test
            t_stat, p_val = stats.ttest_rel(post_scores, pre_scores)
            p_values[question] = p_val
        
        # Create summary dataframe
        summary = pd.DataFrame({
            'Mean_Difference': mean_diffs,
            'Std_Deviation': std_diffs,
            'P_Value': pd.Series(p_values)
        })
        
        # Add significance indicator
        summary['Significant'] = summary['P_Value'] < 0.05
        
        return summary
    
    def plot_pre_post_comparison(self):
        """Plot comparison between pre and post questionnaire scores"""
        merged_data = self.merge_pre_post_data()
        
        # Calculate mean scores for pre and post
        pre_means = {self.pre_question_map[col]: merged_data[f"{col}_pre"].mean() for col in self.scale_cols_pre}
        post_means = {self.pre_question_map[col]: merged_data[f"{col}_post"].mean() for col in self.scale_cols_pre}
        
        # Create dataframe for plotting
        plot_data = pd.DataFrame({
            'Question': list(pre_means.keys()),
            'PRE Score': list(pre_means.values()),
            'POST Score': list(post_means.values())
        })
        
        # Reshape for seaborn
        plot_data_melted = pd.melt(
            plot_data, 
            id_vars=['Question'], 
            value_vars=['PRE Score', 'POST Score'],
            var_name='Questionnaire', 
            value_name='Score'
        )
        
        # Create plot
        plt.figure(figsize=(14, 8))
        chart = sns.barplot(x='Question', y='Score', hue='Questionnaire', data=plot_data_melted)
        chart.set_xticklabels(chart.get_xticklabels(), rotation=45, horizontalalignment='right')
        plt.title('Comparison of PRE and POST Questionnaire Scores', fontsize=16)
        plt.ylim(0, 5)  # Assuming 1-5 scale
        plt.tight_layout()
        
        # Save figure
        plt.savefig(self.output_dir / 'pre_post_comparison.png', dpi=300)
        plt.close()
        
        # Also create a difference plot
        diff_data = self.calculate_score_differences()
        mean_diffs = diff_data.drop(['username', 'source'], axis=1).mean().sort_values()
        
        plt.figure(figsize=(14, 8))
        colors = ['red' if x < 0 else 'green' for x in mean_diffs]
        chart = sns.barplot(x=mean_diffs.index, y=mean_diffs.values, palette=colors)
        chart.set_xticklabels(chart.get_xticklabels(), rotation=45, horizontalalignment='right')
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.title('Mean Difference (POST - PRE) in Questionnaire Scores', fontsize=16)
        plt.tight_layout()
        
        # Save figure
        plt.savefig(self.output_dir / 'score_differences.png', dpi=300)
        plt.close()
    
    def analyze_interaction_patterns(self):
        """Analyze interaction patterns from session logs"""
        if self.logs_data is None:
            print("No session logs available for analysis")
            return None
        
        # Parse the data column which contains JSON
        try:
            # Extract participant_id and event_type for analysis
            self.logs_data['participant_id'] = self.logs_data['data'].apply(
                lambda x: eval(x).get('participant_id', 'unknown') if isinstance(x, str) else 'unknown'
            )
            
            self.logs_data['event_type_detail'] = self.logs_data['data'].apply(
                lambda x: eval(x).get('event_type', 'unknown') if isinstance(x, str) else 'unknown'
            )
            
            # Count interactions by type and participant
            interaction_counts = self.logs_data.groupby(['participant_id', 'event_type_detail']).size().unstack(fill_value=0)
            
            # Calculate total interactions per participant
            interaction_counts['total_interactions'] = interaction_counts.sum(axis=1)
            
            # Calculate interaction rate (interactions per minute)
            # First, get session duration for each participant
            session_starts = self.logs_data[self.logs_data['event_type'] == 'session_start'].copy()
            session_ends = self.logs_data.groupby('participant_id')['timestamp'].max().reset_index()
            
            session_durations = pd.merge(
                session_starts[['participant_id', 'timestamp']], 
                session_ends,
                on='participant_id', 
                suffixes=('_start', '_end')
            )
            
            # Convert timestamps to datetime if they're not already
            session_durations['timestamp_start'] = pd.to_datetime(session_durations['timestamp_start'])
            session_durations['timestamp_end'] = pd.to_datetime(session_durations['timestamp_end'])
            
            # Calculate duration in minutes
            session_durations['duration_minutes'] = (
                session_durations['timestamp_end'] - session_durations['timestamp_start']
            ).dt.total_seconds() / 60
            
            # Merge with interaction counts
            interaction_analysis = pd.merge(
                interaction_counts.reset_index(), 
                session_durations[['participant_id', 'duration_minutes']],
                on='participant_id'
            )
            
            # Calculate interaction rate
            interaction_analysis['interaction_rate'] = interaction_analysis['total_interactions'] / interaction_analysis['duration_minutes']
            
            return interaction_analysis
        except Exception as e:
            print(f"Error analyzing interaction patterns: {e}")
            return None
    
    def analyze_mental_models(self):
        """
        Analyze mental models based on questionnaire responses
        This is a simplified approach - in reality, you would need more detailed qualitative analysis
        """
        # Extract relevant columns from post-questionnaire
        if 'prototype_keywords' in self.post_data.columns and 'interactions_used' in self.post_data.columns:
            keywords_data = self.post_data[['username', 'prototype_keywords', 'interactions_used']].copy()
            
            # Process keywords
            # Assuming keywords are stored as comma-separated values
            all_keywords = []
            for keywords in keywords_data['prototype_keywords'].dropna():
                if isinstance(keywords, str):
                    all_keywords.extend([k.strip() for k in keywords.split(',')])
            
            keyword_counts = pd.Series(all_keywords).value_counts()
            
            # Process interactions used
            # Assuming interactions are stored as Python list representation
            all_interactions = []
            for interactions in keywords_data['interactions_used'].dropna():
                if isinstance(interactions, str):
                    # Clean the string representation of a list
                    clean_str = interactions.replace('[', '').replace(']', '').replace("'", "")
                    all_interactions.extend([i.strip() for i in clean_str.split(',')])
            
            interaction_counts = pd.Series(all_interactions).value_counts()
            
            return {
                'keyword_counts': keyword_counts,
                'interaction_counts': interaction_counts
            }
        else:
            print("Required columns not found in post-questionnaire data")
            return None
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive analysis report"""
        # Check if data is available
        if self.pre_data is None or self.post_data is None:
            print("\nERROR: Cannot generate report because data could not be loaded.")
            print("Please check that the file exists and is accessible.")
            print(f"Looking for file at: {os.path.abspath(self.excel_path)}")
            return
            
        # 1. Pre-Post Differences Analysis
        print("\n=== PRE-POST QUESTIONNAIRE DIFFERENCES ===\n")
        diff_summary = self.analyze_pre_post_differences()
        if not diff_summary.empty:
            print(diff_summary)
        
        # Save to CSV
        diff_summary.to_csv(self.output_dir / 'pre_post_differences.csv')
        
        # 2. Generate visualizations
        print("\n=== GENERATING VISUALIZATIONS ===\n")
        self.plot_pre_post_comparison()
        
        # 3. Interaction Pattern Analysis
        print("\n=== INTERACTION PATTERN ANALYSIS ===\n")
        interaction_analysis = self.analyze_interaction_patterns()
        if interaction_analysis is not None:
            print(interaction_analysis)
            interaction_analysis.to_csv(self.output_dir / 'interaction_analysis.csv')
        
        # 4. Mental Models Analysis
        print("\n=== MENTAL MODELS ANALYSIS ===\n")
        mental_models = self.analyze_mental_models()
        if mental_models is not None:
            print("Top keywords used to describe the prototype:")
            print(mental_models['keyword_counts'])
            
            print("\nInteractions used by participants:")
            print(mental_models['interaction_counts'])
            
            # Save to CSV
            mental_models['keyword_counts'].to_csv(self.output_dir / 'keyword_counts.csv')
            mental_models['interaction_counts'].to_csv(self.output_dir / 'interaction_counts.csv')
        
        print("\n=== ANALYSIS COMPLETE ===\n")
        print(f"Results saved to {self.output_dir.absolute()}")

if __name__ == "__main__":
    # Create analysis object
    analysis = FeedAnalysis()
    
    # Generate comprehensive report
    analysis.generate_comprehensive_report()
