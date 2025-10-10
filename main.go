package main

import (
	"flag"
	"os"

	"gopkg.in/yaml.v3"

	"log/slog"

	"github.com/g-kovacs/random-traffic-mqtt/src/config"
)

func getLogLevel(level config.Loglevel) slog.Level {
	var lvl slog.Level
	switch level {
	case config.Debug:
		lvl = slog.LevelDebug
	case config.Info:
		lvl = slog.LevelInfo
	case config.Error:
		lvl = slog.LevelError
	case config.Warn:
	default:
		lvl = slog.LevelWarn
	}
	return lvl
}

func initConfig(path string) (*config.Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg config.Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func main() {
	slog.Info("Starting application...")

	configPath := flag.String("config", "config.yaml", "Path to the YAML config file")
	flag.Parse()

	cfg, err := initConfig(*configPath)
	if err != nil {
		slog.Error("failed to load config", "path", *configPath)
		os.Exit(-1)
	}
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
		Level: getLogLevel(*cfg.Loglevel), AddSource: true})))
	slog.Debug("config loaded", "config", *cfg)
}
