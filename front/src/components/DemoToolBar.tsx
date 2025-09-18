import React, { useEffect, useRef, useState } from "react";
import styled, { keyframes } from "styled-components";
import { Pause, Play } from "lucide-react";
import { TIME_TO_NEXT_TASK } from "../config.ts";

const draw = keyframes`
  from {
    stroke-dashoffset: 125.6;
  }
  to {
    stroke-dashoffset: 0;
  }
`;

// Контейнер для всех кнопок
const ToolBar = styled.div`
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  @media (max-width: 900px) {
    bottom: 50%;
    transform: translateY(50%);
  }

  @media print {
    display: none;
  }
`;

// Одиночная кнопка
const ToolBarButton = styled.div`
  position: relative; /* создаём контекст для абсолютного позиционирования SVG */
  box-sizing: border-box; /* чтобы width/height включали padding */
  background-color: #1f1f1f;
  padding: 0.5rem;
  border-radius: 40px;
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 45px;
  height: 45px;
  cursor: pointer;
  @media (max-width: 900px) {
    background-color: #2d2d2d;
  }
`;

// SVG-контейнер для круга
const ProgressRing = styled.svg.attrs({
  viewBox: "0 0 45 45",
})`
  position: absolute;
  top: 0;
  left: 0;
  width: 45px;
  height: 45px;
  transform: rotate(-90deg);
`;

// Сам круг с анимацией
const Circle = styled.circle.attrs({
  cx: 22.5,
  cy: 22.5,
  r: 20,
})`
  fill: transparent;
  stroke: white; /* цвет обводки */
  stroke-width: 2;
  stroke-dasharray: 125.6; /* приблизительно 2π·20 */
  stroke-dashoffset: 125.6; /* скрываем всю обводку */
  animation: ${draw} ${TIME_TO_NEXT_TASK}s linear forwards;
`;

interface DemoToolBarProps {
  /** Когда этот проп ставится в true, запускается анимация обводки */
  isFinished: boolean;
  onContinue: () => void;
}

const DemoToolBar: React.FC<DemoToolBarProps> = ({
  isFinished,
  onContinue,
}) => {
  const [showProgress, setShowProgress] = useState(false);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // как только isFinished становится true, показываем обводку и запускаем таймер
    if (isFinished && !paused) {
      setShowProgress(true);
      timerRef.current = setTimeout(() => {
        onContinue();
      }, TIME_TO_NEXT_TASK * 1000);
    }
    // если isFinished стал false (сбросили), то просто очистим таймер
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isFinished, onContinue]);

  const handlePauseClick = () => {
    // при паузе прячем обводку и отменяем таймер
    setShowProgress(false);
    setPaused((val) => !val);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };
  return (
    <ToolBar>
      <ToolBarButton
        onClick={handlePauseClick}
        style={{ border: paused ? "2px solid white" : "none" }}
      >
        <Pause size={22} />
      </ToolBarButton>
      <ToolBarButton onClick={onContinue}>
        {showProgress && (
          <ProgressRing>
            <Circle />
          </ProgressRing>
        )}
        <Play size={24} />
      </ToolBarButton>
    </ToolBar>
  );
};

export default DemoToolBar;
