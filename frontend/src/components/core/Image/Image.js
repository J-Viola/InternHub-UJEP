import React, { useState } from "react";
import Container from "@core/Container/Container";

export default function Image({ 
    src, 
    alt = "Obrázek", 
    property = "", 
    fallbackSrc = null,
    width = "auto",
    height = "auto",
    objectFit = "cover",
    borderRadius = "0",
    onClick = null,
    loading = "lazy"
}) {
    const [imageError, setImageError] = useState(false);
    const [imageLoading, setImageLoading] = useState(true);

    const handleImageLoad = () => {
        setImageLoading(false);
        setImageError(false);
    };

    const handleImageError = () => {
        setImageLoading(false);
        setImageError(true);
    };

    const getImageSrc = () => {
        if (imageError && fallbackSrc) {
            return fallbackSrc;
        }
        return src;
    };

    const isBase64 = src && src.startsWith('data:image');

    const defaultStyles = {
        width: width,
        height: height,
        objectFit: objectFit,
        borderRadius: borderRadius,
        transition: "opacity 0.3s ease-in-out",
        opacity: imageLoading ? 0 : 1
    };

    return (
        <Container property={`relative ${property}`}>
            {imageLoading && (
                <Container 
                    property="absolute inset-0 bg-gray-200 animate-pulse flex items-center justify-center"
                    style={{ borderRadius }}
                >
                    <Container property="text-gray-400 text-sm">Načítání...</Container>
                </Container>
            )}
            
            <img
                src={getImageSrc()}
                alt={alt}
                className={`${imageLoading ? "opacity-0" : "opacity-100"} ${onClick ? "cursor-pointer" : ""}`}
                style={defaultStyles}
                onLoad={handleImageLoad}
                onError={handleImageError}
                onClick={onClick}
                loading={loading}
            />
            
            {imageError && !fallbackSrc && (
                <Container 
                    property="absolute inset-0 bg-gray-100 flex items-center justify-center"
                    style={{ borderRadius }}
                >
                    <Container property="text-gray-400 text-sm">
                        <svg className="w-8 h-8 mb-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
                        </svg>
                        Obrázek není k dispozici
                    </Container>
                </Container>
            )}
        </Container>
    );
} 