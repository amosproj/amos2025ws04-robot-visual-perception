/*
 * SPDX-FileCopyrightText: 2025 robot-visual-perception
 *
 * SPDX-License-Identifier: MIT
 */

import { ReactNode, useState } from 'react';

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

export interface TabbedWidgetPanelProps {
  tabs: Tab[];
  defaultTab?: string;
}

export function TabbedWidgetPanel({
  tabs,
  defaultTab,
}: TabbedWidgetPanelProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  const activeContent = tabs.find((tab) => tab.id === activeTab)?.content;

  return (
    <div className="bg-theme-bg-secondary/95 backdrop-blur-sm border border-theme-border-subtle rounded-lg shadow-xl overflow-hidden">
      {/* Tab buttons */}
      <div className="flex border-b border-theme-border-subtle">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              flex-1 px-3 py-2 sm:px-5 sm:py-3 text-base sm:text-lg md:text-xl lg:text-2xl font-semibold uppercase tracking-wider
              transition-colors duration-200
              ${
                activeTab === tab.id
                  ? 'text-theme-accent border-b-2 border-theme-accent bg-theme-bg-tertiary/50'
                  : 'text-theme-text-muted hover:text-theme-text-primary hover:bg-theme-bg-tertiary/30'
              }
            `}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-4 sm:p-6 md:p-8 max-h-[calc(100vh-var(--ui-header-height)-4rem)] overflow-y-auto">
        {activeContent}
      </div>
    </div>
  );
}

export default TabbedWidgetPanel;
