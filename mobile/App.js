import React from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";

import { SessionProvider } from "./src/SessionContext";
import HomeScreen from "./src/screens/HomeScreen";
import PlanScreen from "./src/screens/PlanScreen";
import LogScreen from "./src/screens/LogScreen";
import { colors } from "./src/theme";

const Tab = createBottomTabNavigator();

const ICONS = { Home: "🏠", Plan: "🗺️", Log: "📝" };

export default function App() {
  return (
    <SessionProvider>
      <StatusBar style="light" />
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={({ route }) => ({
            headerShown: false,
            tabBarActiveTintColor: colors.accent,
            tabBarInactiveTintColor: colors.textMuted,
            tabBarStyle: { backgroundColor: colors.card, borderTopColor: colors.border },
            tabBarIcon: ({ focused }) => (
              <Text style={{ fontSize: focused ? 22 : 18 }}>{ICONS[route.name]}</Text>
            ),
          })}
        >
          <Tab.Screen name="Home" component={HomeScreen} />
          <Tab.Screen name="Plan" component={PlanScreen} />
          <Tab.Screen name="Log" component={LogScreen} />
        </Tab.Navigator>
      </NavigationContainer>
    </SessionProvider>
  );
}
