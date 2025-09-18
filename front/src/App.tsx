import React, { useState } from "react";
import styled from "styled-components";
import Chat from "./components/Chat";
import { SettingsProvider } from "./components/Settings.tsx";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar.tsx";
import DemoSettings from "./components/DemoSettings.tsx";
import { DemoItemsProvider, useDemoItems } from "./hooks/DemoItemsProvider.tsx";
import DemoChat from "./components/DemoChat.tsx";

const AppContainer = styled.div`
  display: flex;
  height: auto;
  width: 100%;
  margin: 0 auto;
  @media print {
    height: auto;
  }
`;

const InnerApp: React.FC = () => {
  const { demoItemsLoaded } = useDemoItems();
  // Можно использовать булево или просто число-счётчик
  const [reloadKey, setReloadKey] = useState(0);

  // эта функция будет прокидываться в SidebarComponent
  const handleNavigateAndReload = () => {
    // переключаем флаг, чтобы сделать новый key у соседнего компонента
    setReloadKey((prev) => prev + 1);
  };
  if (!demoItemsLoaded) {
    return null;
  }
  return (
    <Sidebar onNewChat={handleNavigateAndReload}>
      <Routes>
        <Route path="/" element={<Chat key={reloadKey} />} />
        <Route path="/threads/:threadId" element={<Chat key={reloadKey} />} />
        <Route
          path="/demo/:demoIndex"
          element={
            <DemoChat key={reloadKey} onContinue={handleNavigateAndReload} />
          }
        />
        <Route path="/demo/settings" element={<DemoSettings />} />
      </Routes>
    </Sidebar>
  );
};

const App: React.FC = () => {
  return (
    <DemoItemsProvider>
      <SettingsProvider>
        <AppContainer>
          <BrowserRouter>
            <InnerApp />
          </BrowserRouter>
        </AppContainer>
      </SettingsProvider>
    </DemoItemsProvider>
  );
};

export default App;
