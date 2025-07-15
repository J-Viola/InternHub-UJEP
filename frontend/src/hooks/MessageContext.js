import React, { createContext, useContext, useState } from 'react';

const MessageContext = createContext();

export function MessageProvider({children}){
    const [messages, setMessages] = useState([]);

    const addMessage = (text, type = 'info') => {
        const id = Date.now();
        const newMessage = {id, text, type};
        setMessages(prev => {
            const updatedMessages = [...prev, newMessage];
            console.log('Aktuální zprávy:', updatedMessages); // debug
            return updatedMessages;
        });

        setTimeout(() => {
            setMessages(prev => prev.filter(msg => msg.id !== id));
        }, 3000) // 3s
    };

    const removeMessage = (id) => {
        setMessages(prev => prev.filter(msg => msg.id !== id));
    };

    return (
        <MessageContext.Provider value={{ messages, addMessage, removeMessage }}>
            {children}
        </MessageContext.Provider>
    );

}
export function useMessage() {
    return useContext(MessageContext);
}