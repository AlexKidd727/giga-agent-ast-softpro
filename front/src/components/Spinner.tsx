import React from "react";
import styled, { keyframes } from "styled-components";
import { Loader } from "lucide-react";

// Анимация крутящегося круга
const spin = keyframes`
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
`;

// Стилизация спинера
const SpinnerWrapper = styled.div<{ size?: string; color?: string }>`
  display: inline-block;
  width: ${({ size }) => size || "5px"};
  height: ${({ size }) => size || "5px"};
  > svg {
    animation: ${spin} 1.2s linear infinite;
  }
`;

interface SpinnerProps {
  size?: string; // размер, например '50px'
  color?: string; // цвет, например '#fff'
}

const Spinner: React.FC<SpinnerProps> = ({ size = "8px", color = "#fff" }) => {
  return (
    <SpinnerWrapper size={size} color={color}>
      <Loader size={12} />
    </SpinnerWrapper>
  );
};

export default Spinner;
