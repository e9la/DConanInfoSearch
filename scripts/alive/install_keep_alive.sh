#!/bin/bash
# 
# Render服务器防休眠监控程序 - VPS快速部署脚本
# 功能：自动安装和配置监控程序，支持systemd服务
# 适用：Ubuntu/Debian/CentOS等Linux系统
# 作者：Yuki
# 版本：1.0
#

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1" >&2
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "检测到root用户，建议使用普通用户运行"
        read -p "是否继续？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 检测操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "无法检测操作系统版本"
        exit 1
    fi
    
    log_info "检测到操作系统: $OS $VER"
}

# 安装Python3和pip
install_python() {
    log_info "检查Python环境..."
    
    if command -v python3 &> /dev/null; then
        python_version=$(python3 --version | cut -d' ' -f2)
        log_info "Python已安装: $python_version"
    else
        log_info "安装Python3..."
        
        if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv
        elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
            sudo yum install -y python3 python3-pip
        else
            log_error "不支持的操作系统，请手动安装Python3"
            exit 1
        fi
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3未安装，请手动安装"
        exit 1
    fi
}

# 安装Python依赖
install_dependencies() {
    log_info "安装Python依赖包..."
    
    # 检查是否需要虚拟环境（Ubuntu 24.04+）
    local use_venv=false
    if [[ "$OS" == *"Ubuntu"* ]] && [[ "${VER%%.*}" -ge 24 ]]; then
        use_venv=true
        log_info "检测到Ubuntu 24.04+，将使用虚拟环境"
    fi
    
    # 创建requirements文件
    cat > /tmp/keep_alive_requirements.txt << EOF
requests>=2.25.0
EOF
    
    if $use_venv; then
        # 使用系统包管理器安装（推荐方式）
        if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
            log_info "使用系统包管理器安装requests..."
            sudo apt update
            sudo apt install -y python3-requests python3-venv python3-full
        fi
    else
        # 传统方式安装
        pip3 install -r /tmp/keep_alive_requirements.txt --user
    fi
    
    rm /tmp/keep_alive_requirements.txt
    log_info "依赖安装完成"
}

# 创建工作目录
setup_directories() {
    local work_dir="$HOME/render-keep-alive"
    
    log_info "创建工作目录: $work_dir"
    
    mkdir -p "$work_dir"/{scripts,logs,config}
    
    # 检查脚本文件位置（考虑多种可能路径）
    local script_file=""
    local config_file=""
    
    # 尝试不同的文件路径
    if [[ -f "scripts/alive/vps_keep_alive.py" ]]; then
        script_file="scripts/alive/vps_keep_alive.py"
        config_file="scripts/alive/keep_alive_config.json"
    elif [[ -f "vps_keep_alive.py" ]]; then
        script_file="vps_keep_alive.py"
        config_file="keep_alive_config.json"
    elif [[ -f "../vps_keep_alive.py" ]]; then
        script_file="../vps_keep_alive.py"
        config_file="../keep_alive_config.json"
    else
        log_error "找不到监控脚本文件，请确保vps_keep_alive.py在当前目录或scripts/alive/目录"
        exit 1
    fi
    
    # 复制文件
    cp "$script_file" "$work_dir/scripts/"
    cp "$config_file" "$work_dir/config/"
    chmod +x "$work_dir/scripts/vps_keep_alive.py"
    
    log_info "脚本文件已复制到工作目录"
    
    # 只返回工作目录路径，不要有其他输出
    printf "%s" "$work_dir"
}

# 创建systemd服务
create_systemd_service() {
    local work_dir="$1"
    local user=$(whoami)
    local service_name="render-keep-alive"
    
    log_info "创建systemd服务..."
    
    # 创建服务文件
    sudo tee "/etc/systemd/system/${service_name}.service" > /dev/null << EOF
[Unit]
Description=Render Server Keep-Alive Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=$user
Group=$user
WorkingDirectory=$work_dir
ExecStart=$(which python3) $work_dir/scripts/vps_keep_alive.py -c $work_dir/config/keep_alive_config.json -d
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

# 环境变量
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$work_dir

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$work_dir

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载systemd
    sudo systemctl daemon-reload
    
    log_info "systemd服务已创建: $service_name"
}

# 配置服务
configure_service() {
    local work_dir="$1"
    local service_name="render-keep-alive"
    
    log_info "配置监控服务..."
    
    # 启用服务
    sudo systemctl enable "$service_name"
    
    # 启动服务
    sudo systemctl start "$service_name"
    
    # 检查状态
    sleep 3
    if sudo systemctl is-active --quiet "$service_name"; then
        log_info "服务启动成功！"
    else
        log_error "服务启动失败，请检查日志"
        sudo systemctl status "$service_name"
        exit 1
    fi
}

# 显示使用说明
show_usage() {
    local work_dir="$1"
    local service_name="render-keep-alive"
    
    echo
    log_info "=== 安装完成！==="
    echo
    echo "工作目录: $work_dir"
    echo "配置文件: $work_dir/config/keep_alive_config.json"
    echo "日志文件: $work_dir/logs/keep_alive.log"
    echo
    echo "服务管理命令："
    echo "  启动服务: sudo systemctl start $service_name"
    echo "  停止服务: sudo systemctl stop $service_name"
    echo "  重启服务: sudo systemctl restart $service_name"
    echo "  查看状态: sudo systemctl status $service_name"
    echo "  查看日志: sudo journalctl -u $service_name -f"
    echo
    echo "手动运行（调试用）："
    echo "  测试运行: python3 $work_dir/scripts/vps_keep_alive.py --test"
    echo "  交互模式: python3 $work_dir/scripts/vps_keep_alive.py"
    echo
    echo "配置修改："
    echo "  编辑配置: nano $work_dir/config/keep_alive_config.json"
    echo "  重载服务: sudo systemctl restart $service_name"
    echo
    log_info "监控程序将每12-14分钟自动访问Render服务器，防止休眠"
}

# 主函数
main() {
    echo
    log_info "🚀 Render服务器防休眠监控程序 - VPS部署脚本"
    echo
    
    # 检查环境
    check_root
    detect_os
    
    # 安装依赖
    install_python
    install_dependencies
    
    # 设置程序
    work_dir=$(setup_directories)
    
    # 询问是否安装为系统服务
    echo
    read -p "是否安装为系统服务（推荐）？(Y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "跳过服务安装，仅完成文件部署"
        echo "手动运行命令: python3 $work_dir/scripts/vps_keep_alive.py"
    else
        create_systemd_service "$work_dir"
        configure_service "$work_dir"
    fi
    
    show_usage "$work_dir"
    
    echo
    log_info "🎉 安装完成！"
}

# 脚本开始
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi