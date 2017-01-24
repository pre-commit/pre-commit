package main


import (
	"fmt"
	"github.com/BurntSushi/toml"
)

type Config struct {
	What string
}

func main() {
	var conf Config
	toml.Decode("What = 'world'\n", &conf)
	fmt.Printf("hello %v\n", conf.What)
}
