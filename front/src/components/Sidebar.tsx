import React, { useState } from "react";
import styled, { keyframes, css } from "styled-components";
import { useNavigate } from "react-router-dom";
import {
  Check,
  ChevronRight,
  Plus,
  Printer,
  Settings as SettingsIcon,
} from "lucide-react";
// @ts-ignore
import LogoImage from "../assets/logo.png";
// @ts-ignore
import QRImage from "../assets/qr.png";
import { useSettings } from "./Settings.tsx";

const SIDEBAR_WIDTH = 250;

const Sidebar = styled.div<{ isOpen: boolean }>`
  position: fixed;
  top: 0;
  left: 0;
  width: ${SIDEBAR_WIDTH}px;
  height: 100%;
  padding: 20px;
  background-color: #212121d9;
  backdrop-filter: blur(20px);
  box-shadow: 0 0 ${(props) => (props.isOpen ? "50px" : `0`)} #00000075;
  border-radius: 0 8px 8px 0;
  z-index: 100;
  transform: translateX(
    ${(props) => (props.isOpen ? "0" : `-${SIDEBAR_WIDTH}px`)}
  );
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease;
  @media (max-width: 900px) {
    border-radius: 0;
  }

  @media print {
    display: none;
  }
`;

const CompanyLink = styled.a`
  display: inline-block;
  padding: 12px 16px;
  margin: 8px 0;
  background: linear-gradient(135deg, #ff6b35, #f7931e, #ffd700);
  background-size: 200% 200%;
  color: #000 !important;
  text-decoration: none;
  font-weight: bold;
  font-size: 14px;
  text-align: center;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);
  transition: all 0.3s ease;
  animation: gradientShift 3s ease infinite;
  position: relative;
  overflow: hidden;

  &:before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
    transition: left 0.5s ease;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(255, 107, 53, 0.5);
    background-size: 100% 100%;
    
    &:before {
      left: 100%;
    }
  }

  &:active {
    transform: translateY(0);
    box-shadow: 0 2px 10px rgba(255, 107, 53, 0.4);
  }

  &:focus {
    outline: 2px solid #ffd700;
    outline-offset: 2px;
  }

  @keyframes gradientShift {
    0% {
      background-position: 0% 50%;
    }
    50% {
      background-position: 100% 50%;
    }
    100% {
      background-position: 0% 50%;
    }
  }

  @media (max-width: 900px) {
    font-size: 12px;
    padding: 10px 12px;
  }
`;

const Overlay = styled.div<{ isOpen: boolean }>`
  display: none;

  /* показываем оверлей только на мобильных */
  @media (max-width: 900px) {
    display: ${(props) => (props.isOpen ? "block" : "none")};
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 50;
  }

  @media print {
    display: none;
  }
`;

const Main = styled.div<{ isOpen: boolean }>`
  display: flex;
  height: 100vh;
  width: 100%;
  margin: 0 auto;
  transition: margin-left 0.3s ease;

  /* на больших экранах сдвигаем, на малых — нет */
  @media (max-width: 900px) {
    max-height: calc(100vh - 75px);
  }
  @media (min-width: 900px) {
    margin-left: ${(props) => (props.isOpen ? `${SIDEBAR_WIDTH}px` : "0")};
  }

  @media print {
    margin-left: 0 !important;
  }
`;

const Opener = styled.button<{ isOpen: boolean }>`
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 200;
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  color: #fff;
  transition: left 0.3s ease;

  @media print {
    & svg {
      display: none;
    }
  }
`;

const Logo = styled.div`
  width: 156px;
  height: 40px;
  background-image: url(${LogoImage});
  background-size: cover;
`;

const QR = styled.div`
  width: 150px;
  height: 150px;
  margin-top: 8px;
  background-image: url(${QRImage});
  background-size: cover;
`;

const GitHubQR = styled.div`
  width: 120px;
  height: 120px;
  margin: 16px 0 8px 0;
  background: linear-gradient(135deg, #24292e, #586069);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
  }

  &:before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.1) 50%, transparent 70%);
    transform: translateX(-100%);
    transition: transform 0.6s ease;
  }

  &:hover:before {
    transform: translateX(100%);
  }
`;

const GitHubIcon = styled.div`
  font-size: 32px;
  color: #fff;
  margin-bottom: 4px;
`;

const GitHubText = styled.div`
  font-size: 10px;
  color: #fff;
  text-align: center;
  font-weight: bold;
  line-height: 1.2;
`;

const MenuItem = styled.div`
  display: flex;
  align-items: center;
  padding: 8px;
  font-size: 14px;
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  &:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }
  svg {
    margin-right: 0.5rem;
  }
`;

const CheckboxContainer = styled.label`
  display: flex;
  align-items: center;
  padding: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #fff;
`;

const HiddenCheckbox = styled.input.attrs({ type: "checkbox" })`
  border: 0;
  clip: rect(0 0 0 0);
  clippath: inset(50%);
  height: 1px;
  margin: -1px;
  overflow: hidden;
  padding: 0;
  position: absolute;
  white-space: nowrap;
  width: 1px;
`;

const StyledCheckbox = styled.div<{ checked: boolean }>`
  width: 16px;
  height: 16px;
  background: ${(p) => (p.checked ? "#4caf50" : "#555")};
  border-radius: 4px;
  transition: all 150ms;
  display: flex;
  align-items: center;
  justify-content: center;
  svg {
    visibility: ${(p) => (p.checked ? "visible" : "hidden")};
  }
`;

interface SidebarProps {
  children: React.ReactNode;
  onNewChat: () => void;
}

const SidebarComponent = ({ children, onNewChat }: SidebarProps) => {
  const navigate = useNavigate();
  const { settings, setSettings } = useSettings();

  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSettings({ ...settings, ...{ sideBarOpen: !settings.sideBarOpen } });
  };

  const handlePrint = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.print();
  };

  const handleSettings = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate("/demo/settings");
  };

  const handleAutoApproveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSettings({ ...settings, ...{ autoApprove: e.target.checked } });
  };

  const handleNewChat = () => {
    navigate("/");
    onNewChat();
  };

  return (
    <>
      <Overlay isOpen={settings.sideBarOpen} onClick={toggle} />
      <Sidebar isOpen={settings.sideBarOpen}>
        <Logo style={{ opacity: 0, marginBottom: "0.5rem" }} />
        <CompanyLink href="https://ast-softpro.ru" target="_blank" rel="noopener noreferrer">
          🚀 AST-SOFTPRO.RU
        </CompanyLink>
        <MenuItem onClick={handleNewChat}>
          <Plus size={24} />
          Новый чат
        </MenuItem>
        <MenuItem onClick={handlePrint}>
          <Printer size={24} />
          Печать
        </MenuItem>
        <MenuItem onClick={handleSettings}>
          <SettingsIcon size={24} />
          Настройки демо
        </MenuItem>
        <CheckboxContainer>
          <HiddenCheckbox
            checked={settings.autoApprove ?? false}
            onChange={handleAutoApproveChange}
          />
          <StyledCheckbox checked={settings.autoApprove ?? false}>
            <Check size={12} />
          </StyledCheckbox>
          <span style={{ marginLeft: 8 }}>Auto Approve</span>
        </CheckboxContainer>
        
        <GitHubQR 
          onClick={() => window.open('https://github.com/AlexKidd727/giga-agent-ast-softpro/tree/main', '_blank')}
          title="Открыть GitHub репозиторий"
        >
          <GitHubIcon>🐙</GitHubIcon>
          <GitHubText>GitHub<br/>Repository</GitHubText>
        </GitHubQR>
        
        <QR />
      </Sidebar>

      <Opener isOpen={settings.sideBarOpen} onClick={toggle}>
        <Logo />
        <ChevronRight
          style={{
            transform: settings.sideBarOpen ? "rotate(180deg)" : "rotate(0)",
            marginLeft: "0.5rem",
          }}
        />
      </Opener>

      <Main isOpen={settings.sideBarOpen}>{children}</Main>
    </>
  );
};

export default SidebarComponent;
