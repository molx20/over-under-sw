/**
 * Simple Markdown Renderer
 * Converts markdown text to styled HTML using Tailwind classes
 */
import React from 'react'

const MarkdownRenderer = ({ content }) => {
  if (!content) {
    return <div className="text-gray-500 dark:text-gray-400">No content available</div>
  }

  // Simple markdown to HTML conversion
  const renderMarkdown = (text) => {
    const lines = text.split('\n')
    const elements = []
    let currentList = []
    let inCodeBlock = false

    lines.forEach((line, index) => {
      // Headers
      if (line.startsWith('### ')) {
        if (currentList.length > 0) {
          elements.push(<ul key={`list-${index}`} className="list-disc list-inside space-y-1 mb-4 text-gray-700 dark:text-gray-300">{currentList}</ul>)
          currentList = []
        }
        elements.push(<h3 key={index} className="text-md font-semibold text-gray-900 dark:text-white mt-4 mb-2">{line.replace('### ', '')}</h3>)
      } else if (line.startsWith('## ')) {
        if (currentList.length > 0) {
          elements.push(<ul key={`list-${index}`} className="list-disc list-inside space-y-1 mb-4 text-gray-700 dark:text-gray-300">{currentList}</ul>)
          currentList = []
        }
        elements.push(<h2 key={index} className="text-lg font-bold text-gray-900 dark:text-white mt-6 mb-3 border-b border-gray-200 dark:border-gray-700 pb-2">{line.replace('## ', '')}</h2>)
      } else if (line.startsWith('# ')) {
        if (currentList.length > 0) {
          elements.push(<ul key={`list-${index}`} className="list-disc list-inside space-y-1 mb-4 text-gray-700 dark:text-gray-300">{currentList}</ul>)
          currentList = []
        }
        elements.push(<h1 key={index} className="text-xl font-bold text-gray-900 dark:text-white mt-8 mb-4">{line.replace('# ', '')}</h1>)
      }
      // Lists
      else if (line.trim().startsWith('- ')) {
        const content = line.trim().substring(2)
        // Parse bold text **text**
        const parsedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-gray-900 dark:text-white">$1</strong>')
        currentList.push(<li key={`li-${index}`} dangerouslySetInnerHTML={{ __html: parsedContent }} />)
      }
      // Bold text as standalone paragraph
      else if (line.trim().startsWith('**') && line.trim().endsWith('**')) {
        if (currentList.length > 0) {
          elements.push(<ul key={`list-${index}`} className="list-disc list-inside space-y-1 mb-4 text-gray-700 dark:text-gray-300">{currentList}</ul>)
          currentList = []
        }
        const text = line.trim().slice(2, -2)
        elements.push(<p key={index} className="font-bold text-gray-900 dark:text-white mb-1">{text}</p>)
      }
      // Regular paragraphs
      else if (line.trim() !== '') {
        if (currentList.length > 0) {
          elements.push(<ul key={`list-${index}`} className="list-disc list-inside space-y-1 mb-4 text-gray-700 dark:text-gray-300">{currentList}</ul>)
          currentList = []
        }
        // Parse bold text **text**
        const parsedContent = line.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-gray-900 dark:text-white">$1</strong>')
        elements.push(<p key={index} className="text-gray-700 dark:text-gray-300 mb-2" dangerouslySetInnerHTML={{ __html: parsedContent }} />)
      }
      // Empty line
      else {
        if (currentList.length > 0) {
          elements.push(<ul key={`list-${index}`} className="list-disc list-inside space-y-1 mb-4 text-gray-700 dark:text-gray-300">{currentList}</ul>)
          currentList = []
        }
      }
    })

    // Flush remaining list
    if (currentList.length > 0) {
      elements.push(<ul key="list-final" className="list-disc list-inside space-y-1 mb-4 text-gray-700 dark:text-gray-300">{currentList}</ul>)
    }

    return elements
  }

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      {renderMarkdown(content)}
    </div>
  )
}

export default MarkdownRenderer
