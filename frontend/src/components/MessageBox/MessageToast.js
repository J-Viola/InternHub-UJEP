import React from 'react';
import { useMessage } from '@hooks/MessageContext';
import { FaInfo } from "react-icons/fa";
import Container from '@core/Container/Container';
import Paragraph from '@core/Text/Paragraph';
import Button from '@core/Button/Button';

function MessageToast() {
  const { messages, removeMessage } = useMessage();

  const getTypeStyles = (type) => {
    switch (type) {
      case 'S':
        return 'bg-green-400';
      case 'E':
        return 'bg-red-400';
      case 'W':
        return 'bg-yellow-400';  
      default:
        // neutral
        return 'bg-blue-400';
    }
  };

  return (
    <Container property="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 space-y-2">
      {messages.map(msg => (
        <Container
          key={msg.id}
          property={`${getTypeStyles(msg.type)} text-white px-6 py-4 rounded-lg shadow-lg flex items-center min-w-[300px]`}
          style={{
            animation: 'slideDown 0.3s ease-out',
          }}
        >
          <Container property="flex-1 flex items-center justify-center gap-3">
            <FaInfo size={24} />
            <Paragraph>{msg.text}</Paragraph>
          </Container>
          <Button
            onClick={() => removeMessage(msg.id)}
            variant="primary"
            property="ml-4 px-2 py-0.5 h-8 w-8 flex items-center justify-center text-lg hover:text-gray-200 bg-transparent border-none shadow-none"
            noVariant={true}
          >
            ×
          </Button>
        </Container>
      ))}
      <style>
        {`
          @keyframes slideDown {
            0% {
              opacity: 0;
              transform: translateY(-10px);
            }
            100% {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}
      </style>
    </Container>
  );
}
export default MessageToast;