import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [functionCall, setFunctionCall] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const newMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, newMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const url = conversationId
        ? `http://localhost:8000/api/chat/${conversationId}`
        : 'http://localhost:8000/api/chat';

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiMessage = { role: 'assistant', content: '' };

      setMessages(prev => [...prev, aiMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');
        
        for (const line of lines) {
          try {
            const parsedChunk = JSON.parse(line);
            
            switch (parsedChunk.type) {
              case 'content':
                aiMessage.content += parsedChunk.content;
                break;
              case 'function_call':
                setFunctionCall(parsedChunk.function);
                aiMessage.content += `\n\n*Calling function: ${parsedChunk.function}*\n\n`;
                break;
              case 'function_response':
                aiMessage.content += `\n\n*Function response:*\n\`\`\`json\n${parsedChunk.content}\n\`\`\`\n\n`;
                setFunctionCall(null);
                break;
              case 'error':
                aiMessage.content += `\n\n*Error:*\n${parsedChunk.content}\n\n`;
                break;
              case 'conversation_id':
                setConversationId(parsedChunk.id);
                console.log('Conversation ID set:', parsedChunk.id);
                break;
              default:
                console.warn('Unknown chunk type:', parsedChunk.type);
            }
            
            setMessages(prev => prev.map((msg, index) => 
              index === prev.length - 1 ? {...msg, content: aiMessage.content} : msg
            ));
          } catch (error) {
            console.error('Error parsing JSON:', error, 'Line:', line);
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'error', content: 'An error occurred. Please try again.' }]);
    } finally {
      setIsLoading(false);
      setFunctionCall(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '600px', maxWidth: '600px', margin: '0 auto' }}>
      <div style={{ flexGrow: 1, overflowY: 'auto', marginBottom: '1rem', padding: '1rem', border: '1px solid #ccc', borderRadius: '4px' }}>
        {messages.map((msg, index) => (
          <div key={index} style={{ marginBottom: '1rem', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
            <div style={{ display: 'inline-block', padding: '0.5rem', backgroundColor: msg.role === 'user' ? '#e6f2ff' : '#f0f0f0', borderRadius: '4px' }}>
              {msg.role === 'user' ? (
                <p>{msg.content}</p>
              ) : (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              )}
            </div>
          </div>
        ))}
        {isLoading && <div style={{ textAlign: 'center' }}>AI is thinking...</div>}
        {functionCall && (
          <div style={{ marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#fff9c4', borderRadius: '4px' }}>
            <p>Function called: {functionCall}</p>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div style={{ display: 'flex' }}>
        <input
          style={{ flexGrow: 1, marginRight: '0.5rem', padding: '0.5rem' }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button onClick={sendMessage} disabled={isLoading} style={{ padding: '0.5rem 1rem' }}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;