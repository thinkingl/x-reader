import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { BookOutlined, UnorderedListOutlined, SettingOutlined, AudioOutlined } from '@ant-design/icons';
import BookList from './pages/BookList';
import BookDetail from './pages/BookDetail';
import TaskList from './pages/TaskList';
import VoicePresets from './pages/VoicePresets';
import Configuration from './pages/Configuration';
import AudioPlayer, { AudioProvider } from './components/AudioPlayer';
import './App.css';

const { Header, Sider, Content } = Layout;

function AppContent() {
  const location = useLocation();

  const menuItems = [
    { key: '/', icon: <BookOutlined />, label: <Link to="/">图书列表</Link> },
    { key: '/tasks', icon: <UnorderedListOutlined />, label: <Link to="/tasks">任务列表</Link> },
    { key: '/presets', icon: <AudioOutlined />, label: <Link to="/presets">语音预设</Link> },
    { key: '/config', icon: <SettingOutlined />, label: <Link to="/config">配置</Link> },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark">
        <div className="logo">x-reader</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px' }}>
          <h2 style={{ margin: 0 }}>电子书转音频系统</h2>
        </Header>
        <Content style={{ margin: '24px', padding: '24px', background: '#fff' }}>
          <Routes>
            <Route path="/" element={<BookList />} />
            <Route path="/books/:id" element={<BookDetail />} />
            <Route path="/tasks" element={<TaskList />} />
            <Route path="/presets" element={<VoicePresets />} />
            <Route path="/config" element={<Configuration />} />
          </Routes>
        </Content>
      </Layout>
      <AudioPlayer />
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AudioProvider>
        <AppContent />
      </AudioProvider>
    </Router>
  );
}

export default App;
